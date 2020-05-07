import threading
import time
import os
import uuid
import platform

if platform.system() == "Windows":
    os.environ["PATH"] = os.environ["PATH"]\
        + ";"\
        + __file__[:-11]\
        + "libav-x86_64-w64-mingw32-11.7/usr/bin".replace("/", os.sep)

import toml
from pydub import AudioSegment
from tinytag import TinyTag

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
runThread = None
thread_active = False
LocalMusicSource = None
config = {}


def _setup_config():
    global config
    config = toml.load("local_music_source/default_config.toml")
    if os.path.exists("local_music_source/config.toml"):
        config.update(toml.load("local_music_source/config.toml"))
    config["track"] = config.get("track", {})
    if config["namespace"] == "00000000-0000-0000-0000-000000000000":
        config["namespace"] = str(uuid.uuid1())


def _register_(serviceList, pluginProperties):
    global services, plugin, core, music_manager, LocalMusicSource
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    music_manager = services["music_manager"][0]
    _setup_config()
    core.addStart(startThread)
    core.addClose(closeThread)

    class LocalMusicSource(music_manager.MusicSource):
        _instances = []

        def __init__(self):
            LocalMusicSource._instances.append(self)
            self._ns = uuid.UUID(config["namespace"])
            self.rescan()

        def get_static_id(self):
            return str(self._ns)

        '''def login(self):
            return self.get_status()'''

        def _write_config(self):
            with open("local_music_source/config.toml", "w") as f:
                toml.dump(config, f)

        def rescan(self):
            self._tracks = {}
            self._images = {}
            directories = config["directory"]
            for d in range(len(directories)):
                p = directories[d]["path"]
                for f in os.listdir(p):
                    u = str(uuid.uuid5(self._ns, p + os.sep + f))
                    self._tracks[u] = config["track"].get(u, {})
                    fp = p + f
                    tag = TinyTag.get(fp, image=True)
                    track = self._tracks[u]
                    track["album"] =\
                        track.get("album", tag.album)
                    track["album_artist"] =\
                        track.get("album_artist", tag.albumartist)
                    track["artist"] =\
                        track.get("artist", tag.artist)
                    track["audio_offset"] =\
                        track.get("audio_offset", tag.audio_offset)
                    track["bitrate"] =\
                        track.get("bitrate", tag.bitrate)
                    track["comment"] =\
                        track.get("comment", tag.comment)
                    track["composer"] =\
                        track.get("composer", tag.composer)
                    track["disc"] =\
                        track.get("disc", tag.disc)
                    track["disc_total"] =\
                        track.get("disc_total", tag.disc_total)
                    track["duration"] =\
                        track.get("duration", tag.duration)
                    track["file_size"] =\
                        track.get("file_size", tag.filesize)
                    track["genre"] =\
                        track.get("genre", tag.genre)
                    track["sample_rate"] =\
                        track.get("sample_rate", tag.samplerate)
                    track["title"] =\
                        track.get("title", tag.title)
                    track["track"] =\
                        track.get("track", tag.track)
                    track["track_total"] =\
                        track.get("track_total", tag.track_total)
                    track["year"] =\
                        track.get("year", tag.year)
                    track["path"] = fp
                    track["type"] = f.split(".")[-1]
                    track["id"] = u
                    if not all(key in track for key in (
                            "frame_width",
                            "channels",
                            "frame_rate",
                            )):
                        track_payload = AudioSegment.from_file(
                            os.path.abspath(track["path"]),
                            track["type"],
                            )
                        track["frame_width"] = track_payload.sample_width
                        track["channels"] = track_payload.channels
                        track["frame_rate"] = track_payload.frame_rate
                    if track["title"] is None:
                        track["title"] = ".".join(f.split(".")[:-1])
                    self._images[u] = tag.get_image()
                    if self._images[u] is not None:
                        self._images[u] = Image.open(BytesIO(self._images[u]))
            config["track"] = self._tracks
            self._write_config()

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

        def get_track(self, trackid):
            track = AudioSegment.from_file(
                self._tracks[trackid]["path"],
                self._tracks[trackid]["type"],
                )
            return track.raw_data
#            samples = track.get_array_of_samples()
#            for sample in samples:
#                yield samples.pop(-1)

        def get_track_art(self, trackid):
            return self._images.get(trackid, None)

        def get_status(self):
            return music_manager.Status.READY

    # replace with lines for multiple directories
    music_manager.add_source(LocalMusicSource())


def loopTask():
    pass


def startThread():
    global runThread, thread_active
    thread_active = True
    runThread = threading.Thread(target=threadScript)
    runThread.start()


def closeThread():
    global runThread, thread_active
    thread_active = False
    runThread.join()


def threadScript():
    global thread_active, LocalMusicSource, config
    while thread_active:
        for instance in LocalMusicSource._instances:
            instance.rescan()
            for tc in range(round(config["rescan_delay"])):
                time.sleep(1)
                if not thread_active:
                    break
            if not thread_active:
                break
    thread_active = False
