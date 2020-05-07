import threading
from collections import namedtuple
import os
import time

services = {}
plugin = {}
core, gui_core, gui_display, music_manager = None, None, None, None
run_thread = None
thread_active = False
_screen_dimen = (512, 512)
_hopper_root = __file__[:-11]
_hopper_images_root = _hopper_root + "images" + os.sep
_hopper_fonts_root = _hopper_root + "fonts" + os.sep
_background = None
MenuOption = namedtuple("MenuOption", "icon text function parameters")


def _register_(serviceList, pluginProperties):
    global services, plugin, core, gui_core, gui_display, music_manager
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    gui_core = services["gui_core"][0]
    gui_display = services["gui_display"][0]
    music_manager = services["music_manager"][0]
    core.addStart(setup)
    # core.add_close(close_thread)
    core.addLoop(loop_task)


def setup():
    global _screen_dimen
    _screen_dimen = gui_display.setup()
    setup_modes()
    gui_core.switch_mode("_start")
    gui_display.set_name("JukePy 2")


_global_hs = None

_play_icon_off, _play_icon_on = None, None
_pause_icon_off, _pause_icon_on = None, None
_song_text, _artist_text, _blocker_background = None, None, None
_play_icon_hs = None

_repeat_icon, _shuffle_icon, _menu_icon, _volume_icon = None, None, None, None
_menu_icon_hs = None

_menu_background, _menu_tab, _menu_tab_text = None, None, None
_menu_area, _menu_hover = None, None
_menu_tab_hs, _menu_global_hs = None, None


def setup_modes():
    global _background
    _background = gui_core.DynamicImage.from_path(
        _hopper_images_root + "sharon-mccutcheon-vcP6w7Q_rjg-unsplash.jpg",
        (0, 0),
        _screen_dimen)
    # Photo by Sharon McCutcheon on Unsplash

    global _global_hs
    _global_hs = gui_core.Hotspot()
    _global_hs.add_binding("key:down:96", action_toggle_menu)
    _global_hs.add_binding("action:play_icon_enter", _play_icon_enter)
    _global_hs.add_binding("action:play_icon_leave", _play_icon_leave)
    _global_hs.add_binding("action:toggle_pause", toggle_pause)
    _global_hs.add_binding("action:toggle_menu", action_toggle_menu)
    _global_hs.add_binding("action:menu_up", menu_up)
    _global_hs.add_binding("action:menu_down", menu_down)
    _global_hs.add_binding("action:increment_tab", increment_tab)
    _global_hs.add_binding("action:decrement_tab", decrement_tab)
    _global_hs.add_binding("action:scroll_down", scroll_down)
    _global_hs.add_binding("action:scroll_up", scroll_up)
    _global_hs.add_binding("action:menu_select", menu_select)

    global _play_icon_off, _play_icon_on, _pause_icon_off, _pause_icon_on
    global _play_icon_hs
    _play_icon_off = gui_core.Icon.from_md_name(
        "play-circle-outline",
        color=(255, 255, 255, 0),
        size=_screen_dimen[0]//5,
        position=(0, _screen_dimen[1]-_screen_dimen[0]//5)
        )
    _play_icon_on = gui_core.Icon.from_md_name(
        "play-circle",
        color=(255, 255, 255, 0),
        size=_screen_dimen[0]//5,
        position=(0, _screen_dimen[1]-_screen_dimen[0]//5)
        )
    _pause_icon_off = gui_core.Icon.from_md_name(
        "pause-circle-outline",
        color=(255, 255, 255, 255),
        size=_screen_dimen[0]//5,
        position=(0, _screen_dimen[1]-_screen_dimen[0]//5)
        )
    _pause_icon_on = gui_core.Icon.from_md_name(
        "pause-circle",
        color=(255, 255, 255, 0),
        size=_screen_dimen[0]//5,
        position=(0, _screen_dimen[1]-_screen_dimen[0]//5)
        )
    _play_icon_hs = gui_core.CircleHotspot(
        (_screen_dimen[0]//10, _screen_dimen[1]-_screen_dimen[0]//10),
        _screen_dimen[0]*0.08  # 0.08 measured after testing
    )
    _play_icon_hs.add_binding("mouse:enter", _play_icon_enter)
    _play_icon_hs.add_binding("mouse:leave", _play_icon_leave)
    _play_icon_hs.add_binding("mouse:click:1", toggle_pause)

    global _song_text, _artist_text, _blocker_background
    _song_text = gui_core.Text.from_truetype(
        "No Song",
        _hopper_fonts_root + "Work_Sans" + os.sep + "static" + os.sep
        + "WorkSans-ExtraBold.ttf",
        (255, 255, 255, 255),
        _screen_dimen[0]//13,
        (_screen_dimen[0]*3//10, _screen_dimen[1]-_screen_dimen[0]//5)
        )
    _artist_text = gui_core.Text.from_truetype(
        "No Artist",
        _hopper_fonts_root + "Work_Sans" + os.sep + "static" + os.sep
        + "WorkSans-ExtraBold.ttf",
        (255, 255, 255, 255),
        _screen_dimen[0]//13,
        (_screen_dimen[0]*3//10, _screen_dimen[1]-_screen_dimen[0]//10)
        )
    _blocker_background = gui_core.Rect(
        (_screen_dimen[0], _screen_dimen[0]//5),
        position=(0, _screen_dimen[1]-_screen_dimen[0]//5),
        color=(20, 20, 40, 200)
        )

    global _repeat_icon, _shuffle_icon, _menu_icon, _volume_icon, _menu_area
    global _menu_icon_hs
    _repeat_icon = gui_core.Icon.from_md_name(
        "repeat-off",
        color=(255, 255, 255, 255),
        size=_screen_dimen[0]//10,
        position=(_screen_dimen[0]//5, _screen_dimen[1]-_screen_dimen[0]//5)
        )
    _shuffle_icon = gui_core.Icon.from_md_name(
        "shuffle-disabled",
        color=(255, 255, 255, 255),
        size=_screen_dimen[0]//10,
        position=(_screen_dimen[0]//5, _screen_dimen[1]-_screen_dimen[0]//10)
        )
    _menu_icon = gui_core.Icon.from_md_name(
        "menu",
        color=(255, 255, 255, 255),
        size=_screen_dimen[0]//8,
        position=(0, 0)
        )
    _volume_icon = gui_core.Icon.from_md_name(
        "volume-high",
        color=(255, 255, 255, 255),
        size=_screen_dimen[0]//8,
        position=(_screen_dimen[0]*7//8, 0)
        )
    _menu_icon_hs = gui_core.RectangleHotspot(
        (0, 0),
        (_screen_dimen[0]//8, _screen_dimen[0]//8)
    )
    _menu_icon_hs.add_binding("mouse:click:1", action_toggle_menu)

    global _menu_background, _menu_tab, _menu_tab_text, _menu_hover
    global _menu_tab_hs, _menu_global_hs
    _menu_background = gui_core.Rect(
        (_screen_dimen[0], _screen_dimen[1]-_screen_dimen[0]//5),
        color=(255, 255, 255, 220)
        )
    _menu_tab = gui_core.Icon.from_md_name(
        "music-note",
        color=(90, 90, 90, 255),
        size=_screen_dimen[0]//8,
        position=(_screen_dimen[0]//8, 0)
        )
    _menu_tab_text = gui_core.Text.from_truetype(
        "Songs",
        _hopper_fonts_root + "Work_Sans" + os.sep + "static" + os.sep
        + "WorkSans-Regular.ttf",
        (90, 90, 90, 255),
        _screen_dimen[0]//10,
        (_screen_dimen[0]*17//64, 0)
        )
    _menu_area = gui_core.SubImage(
        (_screen_dimen[0],
         _screen_dimen[1]-_screen_dimen[0]//5-_screen_dimen[0]//8),
        (0, _screen_dimen[0]//8)
    )
    _menu_hover = gui_core.Rect((_screen_dimen[0], _screen_dimen[0]//8),
                                (20, 20, 40, 128))
    _menu_tab_hs = gui_core.RectangleHotspot(
        (_screen_dimen[0]//8, 0),
        (_screen_dimen[0]*3//4, _screen_dimen[0]//8)
    )
    _menu_tab_hs.add_binding("mouse:click:1", increment_tab)
    _menu_global_hs = gui_core.Hotspot()
    _menu_global_hs.add_binding("key:down:273", menu_up)
    _menu_global_hs.add_binding("key:down:274", menu_down)
    _menu_global_hs.add_binding("key:down:275", increment_tab)
    _menu_global_hs.add_binding("key:down:276", decrement_tab)
    _menu_global_hs.add_binding("key:down:115", scroll_down)
    _menu_global_hs.add_binding("key:down:119", scroll_up)
    _menu_global_hs.add_binding("key:down:100", increment_tab)
    _menu_global_hs.add_binding("key:down:97", decrement_tab)
    _menu_global_hs.add_binding("key:down:13", menu_select)

    setup_mode_start()
    setup_mode_playing()
    setup_mode_menu()


_mode_start_time = 0


def setup_mode_start():
    logo = gui_core.DynamicImage.from_path_static_resize(
        _hopper_images_root + "JukePiLogo.png",
        (_screen_dimen[0]//4, _screen_dimen[1]//2 - _screen_dimen[0]//4),
        (_screen_dimen[0]//2, _screen_dimen[1]//2)
        )
    version = gui_core.Text.from_truetype(
        "JukePi - 0.1.0", r"AGENCYB.TTF", (255, 255, 255), 16, (0, 0))
    gui_core.define_mode("_start", [_background, logo, version], [])


_play_icon_hover = False


def setup_mode_playing():
    gui_core.define_mode("_playing", [_background,
                                      _menu_icon,
                                      _volume_icon,
                                      _blocker_background,
                                      _play_icon_off,
                                      _play_icon_on,
                                      _pause_icon_off,
                                      _pause_icon_on,
                                      _shuffle_icon,
                                      _repeat_icon,
                                      _song_text,
                                      _artist_text],
                                     [_global_hs,
                                      _menu_icon_hs,
                                      _play_icon_hs
                                      ])


def setup_mode_menu():
    gui_core.define_mode("_menu", [_background,
                                   _menu_background,
                                   _menu_icon,
                                   _menu_tab,
                                   _menu_tab_text,
                                   _volume_icon,
                                   _menu_area,
                                   _blocker_background,
                                   _play_icon_off,
                                   _play_icon_on,
                                   _pause_icon_off,
                                   _pause_icon_on,
                                   _shuffle_icon,
                                   _repeat_icon,
                                   _song_text,
                                   _artist_text],
                                  [_global_hs,
                                   _menu_global_hs,
                                   _menu_icon_hs,
                                   _menu_tab_hs,
                                   _play_icon_hs
                                   ])
    global _menu_tabs
    _menu_tabs = [
        {"title": "Songs",
         "icon": "music-note",
         "options": []
         },
        {"title": "Playlists",
         "icon": "playlist-music",
         "options": []
         },
        {"title": "Artists",
         "icon": "account-music",
         "options": []
         },
        {"title": "Albums",
         "icon": "album",
         "options": []
         },
        {"title": "Settings",
         "icon": "cog",
         "options": [
             MenuOption(
                gui_core.Icon.from_md_name(
                    "play-speed",
                    color=(90, 90, 90, 255),
                    size=_screen_dimen[0]//8,
                    position=()
                    ),
                "Play Speed",
                print,
                ("Print called on Play Speed",)
                ),
             MenuOption(
                gui_core.Icon.from_md_name(
                    "volume-high",
                    color=(90, 90, 90, 255),
                    size=_screen_dimen[0]//8,
                    position=()
                    ),
                "Volume",
                print,
                ("Print called on Volume",)
                ),
             MenuOption(
                gui_core.Icon.from_md_name(
                    "download",
                    color=(90, 90, 90, 255),
                    size=_screen_dimen[0]//8,
                    position=()
                    ),
                "Sources",
                print,
                ("Print called on Sources",)
                ),
             MenuOption(
                gui_core.Icon.from_md_name(
                    "monitor",
                    color=(90, 90, 90, 255),
                    size=_screen_dimen[0]//8,
                    position=()
                    ),
                "Display",
                print,
                ("Print called on Display",)
                ),
             ]
         },
    ]
    _update_menu()


def _play_icon_enter(coords):
    global _play_icon_hover
    _play_icon_hover = True
    _update_play_icon()


def _play_icon_leave(coords):
    global _play_icon_hover
    _play_icon_hover = False
    _update_play_icon()


_menu_tabs = None
_menu_tab_index = 0
_menu_scroll = 0


def action_toggle_menu(coords):
    if gui_core.mode == "_menu":
        gui_core.switch_mode("_playing")
        _menu_icon.update_text(_menu_tab.get_md_character("menu"))
        _menu_icon.update_color((255, 255, 255, 255))
        _volume_icon.update_color((255, 255, 255, 255))
    else:
        gui_core.switch_mode("_menu")
        _menu_icon.update_text(_menu_tab.get_md_character("menu-open"))
        _menu_icon.update_color((90, 90, 90, 255))
        _volume_icon.update_color((90, 90, 90, 255))


def increment_tab(coords):
    global _menu_tab_index
    _menu_tab_index = (_menu_tab_index + 1) % len(_menu_tabs)
    _update_menu()


def decrement_tab(coords):
    global _menu_tab_index
    _menu_tab_index = (_menu_tab_index - 1) % len(_menu_tabs)
    _update_menu()


_menu_option_texts = []
_menu_hover_index = 0


def _update_menu(reset_scroll=True):
    global _menu_option_texts, _menu_hover_index
    if reset_scroll:
        global _menu_scroll
        _menu_scroll = 0
    tab = _menu_tabs[_menu_tab_index]
    _menu_tab.update_text(_menu_tab.get_md_character(tab["icon"]))
    _menu_tab_text.update_text(tab["title"])
    if _menu_tab_index == 0:
        fill_songs()
    _menu_hover_index = 0
    _menu_area.compositing_order = [_menu_hover]
    _menu_option_texts = []
    position = -_menu_scroll
    for option in tab["options"]:
        try:
            offset = option.icon.offset
        except AttributeError:
            offset = option.icon.offset = option.icon.position
        try:
            option.icon.position = (offset[0], offset[1] + position)
        except IndexError:
            offset = option.icon.offset = (0, 0)
            option.icon.position = (0, position)
        _menu_area.compositing_order.append(option.icon)
        _menu_option_texts.append(
            gui_core.Text.from_truetype(
                option.text,
                _hopper_fonts_root + "Work_Sans" + os.sep + "static" + os.sep
                + "WorkSans-Regular.ttf",
                (90, 90, 90, 255),
                _screen_dimen[0]//10,
                (_screen_dimen[0]*9//64, position)
            )
        )
        _menu_option_texts[-1].draw = False
        _menu_area.compositing_order.append(_menu_option_texts[-1])
        position += _screen_dimen[0]//8
    draw_menu_area(tab)


def draw_menu_area(tab):
    # _menu_area.compositing_order = []
    position = -_menu_scroll
    _menu_hover.position = (0, -_screen_dimen[0]//4)
    for option_index in range(len(tab["options"])):
        option = tab["options"][option_index]
        if -_screen_dimen[0]//8 <= position < _menu_area.dimensions[1]:
            try:
                offset = option.icon.offset
            except AttributeError:
                offset = option.icon.offset = option.icon.position
            try:
                option.icon.position = (offset[0], offset[1] + position)
            except IndexError:
                offset = option.icon.offset = (0, 0)
                option.icon.position = (0, position)
            _menu_option_texts[option_index].position = \
                (_screen_dimen[0]*9//64, position)
            option.icon.draw = True
            _menu_option_texts[option_index].draw = True
            color = (90, 90, 90, 255)
            if _menu_hover_index == option_index:
                _menu_hover.position = (0, position)
                color = (255, 255, 255, 255)
            _menu_option_texts[option_index].update_color(color)
            if isinstance(option.icon, (gui_core.Text, gui_core.Icon)):
                option.icon.update_color(color)
        else:
            option.icon.draw = False
            _menu_option_texts[option_index].draw = False
        position += _screen_dimen[0]//8


def scroll(position):
    global _menu_scroll
    _menu_scroll = clamp(
        position,
        0,
        _screen_dimen[0]//8 * len(_menu_tabs[_menu_tab_index]["options"])
        - _menu_area.dimensions[1])
    draw_menu_area(_menu_tabs[_menu_tab_index])


def scroll_down(coords=(0, 0), amount=None):
    if amount is None:
        amount = _screen_dimen[0]//8
    scroll(_menu_scroll + amount)


def scroll_up(coords=(0, 0), amount=None):
    if amount is None:
        amount = _screen_dimen[0]//8
    scroll(_menu_scroll - amount)


def menu_down(coords=(0, 0)):
    global _menu_hover_index
    _menu_hover_index = clamp(_menu_hover_index + 1, 0,
                              len(_menu_tabs[_menu_tab_index]["options"]) - 1)
    scroll(((_menu_hover_index - 2) * _screen_dimen[0]//8))


def menu_up(coords=(0, 0)):
    global _menu_hover_index
    _menu_hover_index = clamp(_menu_hover_index - 1, 0,
                              len(_menu_tabs[_menu_tab_index]["options"]) - 1)
    scroll(((_menu_hover_index - 2) * _screen_dimen[0]//8))


def menu_select(coords=(0, 0)):
    if 0 <= _menu_hover_index < len(_menu_tabs[_menu_tab_index]["options"]):
        option = _menu_tabs[_menu_tab_index]["options"][_menu_hover_index]
        # print(*option.parameters)
        option.function(*option.parameters)
    else:
        print("invalid _menu_hover_index")


def play_song(song, title, artist):
    music_manager.set_queue([[song]], [(0, 0)])
    music_manager.set_playing(True)
    _song_text.update_text(title)
    _artist_text.update_text(artist)


def toggle_pause(coords=(0, 0)):
    music_manager.set_playing(not music_manager.get_playing())


def fill_songs():
    _menu_tabs[0]["options"] = []
    for song in music_manager.get_songs():
        track = next(song.source.get_track_data(song.id))
        img = song.source.get_track_art(song.id)
        if img is None:
            icon = gui_core.Icon.from_md_name(
                "music-circle",
                color=(90, 90, 90, 255),
                size=_screen_dimen[0]//8,
                position=(0, 0)
                )
        else:
            icon = gui_core.DynamicImage(
                img.resize((_screen_dimen[0]//8, _screen_dimen[0]//8), 1)
            )
        _menu_tabs[0]["options"].append(
            MenuOption(
                icon,
                track["title"],
                play_song,
                (song, track["title"], track["artist"])))


_playing_state = False
_play_icon_hover_state = False


def _update_play_icon():
    global _playing_state, _play_icon_hover_state
    if _playing_state != music_manager.get_playing() \
            or _play_icon_hover_state != _play_icon_hover:
        _playing_state = music_manager.get_playing()
        _play_icon_hover_state = _play_icon_hover
        if music_manager.get_playing():
            _pause_icon_on.update_color((255, 255, 255, 0))
            _pause_icon_off.update_color((255, 255, 255, 0))
            if _play_icon_hover:
                _play_icon_on.update_color((255, 255, 255, 255))
                _play_icon_off.update_color((255, 255, 255, 0))
            else:
                _play_icon_on.update_color((255, 255, 255, 0))
                _play_icon_off.update_color((255, 255, 255, 255))
        else:
            _play_icon_on.update_color((255, 255, 255, 0))
            _play_icon_off.update_color((255, 255, 255, 0))
            if _play_icon_hover:
                _pause_icon_on.update_color((255, 255, 255, 255))
                _pause_icon_off.update_color((255, 255, 255, 0))
            else:
                _pause_icon_on.update_color((255, 255, 255, 0))
                _pause_icon_off.update_color((255, 255, 255, 255))


def loop_task():
    _update_play_icon()
    gui_display.draw()
    if gui_core.mode == "_start":
        global _mode_start_time
        if _mode_start_time == 0:
            _mode_start_time = millis()
        elif millis() > _mode_start_time + 1000:
            gui_core.switch_mode("_playing")
            _mode_start_time = 0


def start_thread():
    global run_thread, thread_active
    thread_active = True
    run_thread = threading.Thread(target=thread_script)
    run_thread.start()


def close_thread():
    global runThread, thread_active
    thread_active = False
    runThread.join()


def thread_script():
    global thread_active
    thread_active = False


def addCommands(structure):
    pass


def addTicket(structure):
    pass


def addCommandData(structure, root):
    pass


def millis():
    return int(round(time.time() * 1000))


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)
