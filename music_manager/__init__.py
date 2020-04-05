import threading
from abc import ABC, abstractmethod
from enum import IntEnum
import collections
from functools import partial
# import time

import pyaudio
from fuzzywuzzy import fuzz

from . import playlib

services = {}
music_sources = []
plugin = {}
core = None
runThread = None
threadActive = False
_queue = None
_queue_items = []
_queue_order = []
_playing = threading.Event()
_stopped = threading.Event()
playing = False
Song = collections.namedtuple("Song", "source id")

_player_state = 0
_player_state_change = threading.Event()
_player_state_change_complete = threading.Event()


def _register_(serviceList, pluginProperties):
    global services, plugin, core
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    # core.addStart(setup)
    core.addStart(startThread)
    core.addClose(closeThread)
    # core.addLoop(loopTask)
    userInterface = services["userInterface"][0]
    userInterface.addCommands(subcommands)
    for set in ["music_manager", "player"]:
        userInterface.addCommands({set: subcommands})
    set_queue([], ())


def loopTask():
    pass


def add_source(source):
    global music_sources
    source.login()
    music_sources.append(source)


def startThread():
    global runThread, threadActive
    threadActive = True
    runThread = threading.Thread(target=threadScript)
    runThread.start()


def closeThread():
    global runThread, threadActive
    threadActive = False
    _playing.set()
    runThread.join()


def player_callback(track, t_data, in_data, frame_count, time_info, status):
    global _frame_counter
    chunk_size = frame_count \
        * t_data["frame_width"] \
        * t_data["channels"]
    if _frame_counter >= 0:
        if len(track) >= _frame_counter + chunk_size:
            data = track[_frame_counter:_frame_counter + chunk_size]
            _frame_counter += chunk_size
            return (data, pyaudio.paContinue)
        else:
            data = track[_frame_counter:]
            _frame_counter = -1
            set_player_state(70, True)
            return (data, pyaudio.paComplete)
    else:
        _frame_counter = -1
        set_player_state(70, True)
        return (b'', pyaudio.paComplete)


def set_player_state(state, unsafe=False):
    global _player_state
    if unsafe:
        _player_state = state
        _player_state_change.set()
    else:
        _player_state_change_complete.clear()
        set_player_state(state, True)
        _player_state_change_complete.wait()


def threadScript():
    global threadActive, _queue, music_sources, _frame_counter
    p = pyaudio.PyAudio()
    stream = None
    song = None
    while threadActive:
        _player_state_change.wait()
        _player_state_change.clear()
        if _player_state == 0:
            # stopped
            if stream is not None:
                # close any existing streams
                stream.stop_stream()
                stream.close()
        elif _player_state == 10:
            # start playing queue
            iter(_queue)
            set_player_state(20, True)
        elif _player_state == 20:
            # start playing new song
            try:
                song = next(_queue)
            except StopIteration:
                set_player_state(0, True)
                continue
            track = music_sources[song.source].get_track(song.id)
            track_data = list(
                music_sources[song.source].get_track_data(song.id)
                )[0]
            _frame_counter = 0
            stream = p.open(
                format=p.get_format_from_width(track_data["frame_width"]),
                channels=track_data["channels"],
                rate=track_data["frame_rate"],
                output=True,
                stream_callback=partial(player_callback, track, track_data)
                )
            set_player_state(30, True)
        elif _player_state == 30:
            # (re)start playing song
            stream.start_stream()
            set_player_state(40, True)
        elif _player_state == 40:
            # song is playing
            # print("playing")
            pass
        elif _player_state == 50:
            # song is pausing
            stream.stop_stream()
            set_player_state(60, True)
        elif _player_state == 60:
            # song is paused
            # print("paused")
            pass
        elif _player_state == 70:
            # song is closing and queue is continuing
            stream.stop_stream()
            stream.close()
            set_player_state(20, True)
        elif _player_state == 80:
            # song is closing and queue is going back one song
            stream.stop_stream()
            stream.close()
            _queue.prev()
            set_player_state(20, True)
        _player_state_change_complete.set()


class Status(IntEnum):
    READY = 0
    ERROR = 1
    WAITING = 2


class MusicSource(ABC):
    def __init__(self):
        pass

    def login(self):
        return self.get_status()

    @abstractmethod
    def get_track_data(self, trackid=None):
        pass

    @abstractmethod
    def get_track(self, trackid):
        pass

    def get_track_art(self, trackid):
        pass

    def get_authors(self):
        pass

    def get_albums(self):
        pass

    def get_playlists(self):
        pass

    @abstractmethod
    def get_status(self):
        pass


def set_queue(items=[], order=[]):
    global _queue, _queue_items, _queue_order
    if _player_state != 0:
        was_stopped = True
        stop()
    else:
        was_stopped = False
    if len(items) == 1 and len(items[0]) < 1:
        items = []
    _queue_items = items
    _queue_order = order
    _queue = playlib.Playlist(items, order)
    if was_stopped:
        set_playing(True)

def set_playing(state):
    if state:
        if _player_state == 0:
            set_player_state(10)
        elif _player_state == 60:
            set_player_state(30)
    else:
        if _player_state == 40:
            set_player_state(50)


def set_shuffle(state):
    _queue.set_shuffle(state)


def set_looping(state):
    _queue.set_loop(state)


def next_song():
    set_player_state(70)


def prev_song():
    set_player_state(80)


def stop():
    set_player_state(0)


def command_set_loop(arguments):
    """
Info:
    Sets the current play queue to loop.

Usage: {0} (state)
    """
    if len(arguments) == 2:
        if isinstance(arguments[1], str):
            arg = arguments[1]
            if arg.lower() in {"t", "true", "y", "yes", "on", "1"}:
                set_looping(True)
            elif arg.lower() in {"f", "false", "n", "no", "off", "0"}:
                set_looping(False)
            else:
                print(f"invalid argument '{arg}'")
    else:
        print("Invalid number of arguments. (Should be 1)")


def command_set_shuffle(arguments):
    """
Info:
    Sets the current play queue to shuffle.

Usage: {0} (state)
    """
    if len(arguments) == 2:
        if isinstance(arguments[1], str):
            arg = arguments[1]
            if arg.lower() in {"t", "true", "y", "yes", "on", "1"}:
                set_shuffle(True)
            elif arg.lower() in {"f", "false", "n", "no", "off", "0"}:
                set_shuffle(False)
            else:
                print(f"invalid argument '{arg}'")
    else:
        print("Invalid number of arguments. (Should be 1)")


def command_play(arguments):
    """
Info:
    Plays the current play queue. Specify songs to clear the queue and start
    fresh.

Usage: {0} [<song> [options] | --id <songid>]...

    -s <source>, --source <source>  Specific source to look under.
    -a <artist>, --artist <artist>  Specific artist to look under.
    """
    if len(arguments) > 1:
        stop()
        command_remove_queue([["remove_queue"]])
        command_add_queue(arguments)
    set_playing(True)
    while _player_state < 40:
        _player_state_change.wait()


def command_pause(arguments):
    """
Info:
    Pauses the player

Usage: {0}
    """
    set_playing(False)


def command_stop(arguments):
    """
Info:
    Stops the player

Usage: {0}
    """
    stop()


def command_next(arguments):
    """
Info:
    Tells the player to move to the next song.

Usage: {0}
    """
    next_song()


def command_prev(arguments):
    """
Info:
    Tells the player to move to the next song.

Usage: {0}
    """
    prev_song()


def command_add_queue(arguments):
    """
Info:
    Adds song(s) to the current play queue.

Usage: {0} [--clear] (<song> [options] | --id <songid>)...

    -s <source>, --source <source>  Specific source to look under.
    -a <artist>, --artist <artist>  Specific artist to look under.
    """
    arguments = arguments[1:]
    if len(arguments) > 0 and arguments[0].lower() == "--clear":
        arguments = arguments[1:]
        items = []
        order = []
    else:
        items = _queue_items
        order = list(_queue_order)
    items.append([])
    while len(arguments) > 0:
        sid = arguments.pop(0)
        if sid.lower() == "--id":
            sid = arguments.pop(0)
            for source in range(len(music_sources)):
                if music_sources[source].get_track_data(sid) is not None:
                    song = Song(source, sid)
                    items[-1].append(song)
                    order.append((len(items)-1, len(items[-1])-1))
                    break
        else:
            args = {}
            while len(arguments) > 0 and arguments[0].startswith("-"):
                key = None
                value = None
                if arguments[0].startswith("--"):
                    if len(arguments[0].split("=")) == 2:
                        kv = arguments.pop(0).split("=")
                        key = kv[0].lower()
                        value = kv[1]
                    elif len(arguments[0].split("=")) == 1:
                        key = arguments.pop(0)[2:].lower()
                        value = arguments.pop(0)
                    else:
                        print("Invalid argument set.")
                        return None
                else:
                    key = arguments.pop(0)[1:]
                    value = arguments.pop(0)
                args[key] = value
            sources = list(range(len(music_sources)))
            if args.get("source", None) is None:
                if args.get("s", None) is None:
                    sources = list(range(len(music_sources)))
                else:
                    args["source"] = args["s"]
                    sources = [int(args["source"])]
            else:
                sources = [int(args["source"])]
            best = search_for_song(sources, sid)
            if best is not None:
                items[-1].append(best[1])
                order.append((len(items)-1, len(items[-1])-1))
            else:
                if args.get("source", None) is None:
                    print(f"Could not find song '{sid}'")
                else:
                    print(f"Could not find song '{sid}' in source "
                          + str(args["source"]) + ".")
    # print(items)
    # print(order)
    set_queue(items, order)


def search_for_song(sources, sid):
    best = None
    for source in sources:
        for track in music_sources[source].get_track_data():
            r = fuzz.partial_ratio(track["title"], sid)
            if r >= 80 and (best is None or best[0] < r):
                best = (r, Song(source, track["id"]))
    if best is None:  # Redo check with lowercase if none > 80%
        for source in sources:
            for track in music_sources[source].get_track_data():
                r = fuzz.partial_ratio(
                    track["title"].lower(),
                    sid.lower())
                if r >= 80 and (best is None or best[0] < r):
                    best = (r, Song(source, track["id"]))
    return best


def command_remove_queue(arguments):
    """
Info:
    Removes song(s) from the current play queue. Don't specify any songs to
    clear the queue.

Usage: {0} [<song> [options] | --id <songid>]...

    -s <source>, --source <source>  Specific source to look under.
    -a <artist>, --artist <artist>  Specific artist to look under.
    """
    set_queue([], ())


def command_list_queue(arguments):
    """
Info:
    Lists the current play queue.

Usage: {0} [options]
    -i, --id      Show song IDs.
    -a, --artist  Show song artists.
    -s, --source  Show song sources.
    """
    args = set()
    for arg in arguments:
        if isinstance(arg, str):
            if arg.startswith("--"):
                if "--id" == arg:
                    args.add("i")
                if "--artist" == arg:
                    args.add("a")
                if "--source" == arg:
                    args.add("s")
            elif arg.startswith("-"):
                for letter in arg[1:]:
                    args.add(letter)
    print(args)


def command_playing(arguments):
    pass


subcommands = {"shuffle": command_set_shuffle,
               "loop": command_set_loop,
               "list_queue": command_list_queue,
               "add_queue": command_add_queue,
               "remove_queue": command_remove_queue,
               "play": command_play,
               "pause": command_pause,
               "stop": command_stop,
               "next": command_next,
               "skip": command_next,
               "prev": command_prev,
               "previous": command_prev,
               }
