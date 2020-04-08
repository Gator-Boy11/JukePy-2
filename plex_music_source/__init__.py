import threading
import time
import os
import uuid
import getpass
import platform
import requests
import io

if platform.system() == "Windows":
    os.environ["PATH"] = os.environ["PATH"]\
        + ";"\
        + __file__[:-11]\
        + "libav-x86_64-w64-mingw32-11.7/usr/bin".replace("/", os.sep)

import toml
#from pydub import AudioSegment
import ffmpeg
import keyring
import plexapi
import plexapi.myplex
import plexapi.audio
#from tinytag import TinyTag

pillow_available = False
try:
    from PIL import Image
    from io import BytesIO
    pillow_available = True
except ImportError:
    pass

services = {}
plugin = {}
core = None
music_manager = None
run_thread = None
thread_active = False
PlexMusicSource = None
config = {}


def _setup_config():
    global config
    config = toml.load("plex_music_source/default_config.toml")
    if os.path.exists("plex_music_source/config.toml"):
        config.update(toml.load("plex_music_source/config.toml"))
    config["server"] = config.get("server", [])
    if config["namespace"] == "00000000-0000-0000-0000-000000000000":
        config["namespace"] = str(uuid.uuid1())


def _register_(serviceList, pluginProperties):
    global services, plugin, core, music_manager, PlexMusicSource
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    music_manager = services["music_manager"][0]
    userInterface = services["userInterface"][0]
    _setup_config()
    userInterface.addCommands({"plex": {"add_server": command_add_plex_server}})
    core.addStart(start_thread)
    core.addClose(close_thread)

    class PlexMusicSource(music_manager.MusicSource):
        _instances = []

        def __init__(self, index):
            self._ready = False
            PlexMusicSource._instances.append(self)
            self._ns = uuid.UUID(config["namespace"])
            self._index = index
            self._conf = config["server"][index]
            self._user = self._conf["username"]
            self._server = self._conf["server"]
            self._section = self._conf["section"]
            self._account = plexapi.myplex.MyPlexAccount(
                self._user,
                keyring.get_password(config["keyring_name"], self._user))
            self._connection = self._account.resource(self._server).connect()
            self._ready = True

            self.rescan()
        '''def login(self):
            return self.get_status()'''

        @classmethod
        def _write_config(self):
            with open("plex_music_source/config.toml", "w") as f:
                toml.dump(config, f)

        def rescan(self):
            if not self._ready:
                return None
            tracks = {}
            images = {}
            for item in self._connection.library.section(self._section).all():
                if isinstance(item, plexapi.audio.Artist):
                    for plex_track in item.tracks():
                        unique = plex_track.key
                        u = str(uuid.uuid5(self._ns, unique))
                        track = {}
                        track["id"] = u
                        track["url"] = plex_track.getStreamURL()
                        track["title"] = plex_track.title
                        track["artist"] = plex_track.artist().title
                        track["album"] = plex_track.album().title
                        track["frame_rate"] = 48000
                        track["frame_width"] = 2
                        track["channels"] = 2
                        tracks[u] = track
            self._tracks = tracks
            self._images = images
            # input("enter")

        def get_track(self, trackid):
            track_data = self._tracks[trackid]
            track = (ffmpeg.input(track_data["url"], )
                     .output('-',
                             format='s16le',
                             acodec='pcm_s16le',
                             ac=track_data["channels"],
                             ar=track_data["frame_rate"])
                     .run_async(cmd="ffmpeg",
                                pipe_stdout=True,
                                quiet=True)
                     )
            track = music_manager.MusicTrack(
                track.stdout,
                music_manager.Song(self, trackid))
            return track

        def get_track_data(self, trackid=None):
            if trackid is None:
                # return self._tracks
                for track in self._tracks:
                    yield self._tracks[track]
            else:
                if trackid in self._tracks.keys():
                    yield self._tracks[trackid]
                else:
                    yield None

        def get_status(self):
            return music_manager.Status.READY

    PlexMusicSource._write_config()
    print("\nScanning plex library, this may take a while... ", end="")
    for i in range(len(config["server"])):
        music_manager.add_source(PlexMusicSource(i))
    print("Done!")
    print("Registering services to plex_music_source... ", end="")
    # input("end")


def start_thread():
    global run_thread, thread_active
    thread_active = True
    run_thread = threading.Thread(target=thread_script)
    run_thread.start()


def close_thread():
    global run_thread, thread_active
    thread_active = False
    run_thread.join()


def thread_script():
    global thread_active, PlexMusicSource, config
    while thread_active:
        for instance in PlexMusicSource._instances:
            instance.rescan()
            time.sleep(config["rescan_delay"])
            if not thread_active:
                break
    thread_active = False


def command_add_plex_server(arguments):
    global config
    print("Please enter your plex username and password.")
    print("Then the server and section you would like to use.")
    username = input("Username: ")
    password = getpass.getpass()
    server = input("Server: ")
    section = input("Section: ")
    keyring.set_password(config["keyring_name"], username, password)
    del password  # delete password asap to help protect it
    servers = config.get("server", [])
    servers.append({})
    servers[-1]["username"] = username
    servers[-1]["server"] = server
    servers[-1]["section"] = section
    config["server"] = servers
    PlexMusicSource._write_config()
    music_manager.add_source(PlexMusicSource(len(config["server"])-1))
