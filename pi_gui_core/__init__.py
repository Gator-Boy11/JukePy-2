import threading
from collections import namedtuple
import os
import json
import time

from PIL import Image, ImageDraw, ImageFont, ImageSequence

Hotspot = namedtuple("Hotspot", "name area hover select")

services = {}
plugin = {}
core = None
music_manager = None
run_thread = None
thread_active = False


def _register_(serviceList, pluginProperties):
    global services, plugin, core, music_manager
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    music_manager = services["music_manager"][0]
    # core.addStart(start_thread)
    # core.addClose(close_thread)
    # core.addLoop(loop_task)


def loop_task():
    pass


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


dimen = (0, 0)
modes = {}
mode = "_start"


def prepare(dimensions):
    global dimen
    dimen = dimensions


def define_mode(mode, compositing_order, hotspots=[]):
    modes[mode] = {}
    modes[mode]["compositing_order"] = compositing_order
    modes[mode]["hotspots"] = hotspots


def edit_mode(mode):
    return modes[mode]


def switch_mode(new_mode):
    global mode
    mode = new_mode


def navigate(direction):
    pass


def navigate_4_way(direction):
    pass


def navigate_8_way(direction):
    pass


def navigate_2_way(direction):
    pass


def select():
    pass


def hover(location):
    for hotspot in modes[mode]["hotspots"]:
        if not hotspot.flags.setdefault("entered", False):
            if hotspot.execute_if_inside("mouse:enter", location):
                hotspot.flags["entered"] = True
        elif hotspot.execute_if_inside("mouse:leave", location, True):
            hotspot.flags["entered"] = False
        if not hotspot.in_area(location):
            for button in hotspot.flags.setdefault("clicked", {}):
                hotspot.flags["clicked"][button] = False


def mouse_down(location, button):
    for hotspot in modes[mode]["hotspots"]:
        hotspot.execute_if_inside(f"mouse:down:{button}", location)
        if hotspot.in_area(location):
            hotspot.flags.setdefault("clicked", {})[button] = True


def mouse_up(location, button):
    for hotspot in modes[mode]["hotspots"]:
        hotspot.execute_if_inside(f"mouse:down:{button}", location)
        if hotspot.flags.setdefault("clicked", {}).setdefault(button, False):
            hotspot.execute_if_inside(f"mouse:click:{button}", location)
        hotspot.flags.setdefault("clicked", {})[button] = False


def trigger(location, binding):
    for hotspot in modes[mode]["hotspots"]:
        hotspot.execute_if_inside(binding, location)


def get_frame():
    frame = Image.new("RGBA", dimen, (0, 0, 0, 0))
    for im in modes[mode]["compositing_order"]:
        im.draw_to(frame)
    return frame


class DynamicImage():
    '''Basic dynamic (or static) image class, used for compositing items onto
    each other. This class accepts PIL (pillow) image (or animation/image
    sequence like a gif) and will display that image with the top left corner
    at position ((0, 0) by default).'''
    size = None
    resample = None
    draw = True

    @classmethod
    def from_path(cls, path, position=(0, 0), size=None, resample=3):
        image = Image.open(path)
        return cls(image, position, size, resample)

    @classmethod
    def from_path_static_resize(cls, path, position=(0, 0), size=None,
                                resample=3):
        image = Image.open(path).resize(size, resample)
        return cls(image, position)

    def __init__(self, image, position=(0, 0), size=None, resample=3):
        self.update_image(image)
        self.position = position
        self.size = size
        self.resample = resample

    def update_image(self, image):
        self._image = image
        self._image_iterator = ImageSequence.Iterator(self._image)
        self._frame_time = int(round(time.time() * 1000))
        self.frame = 0

    def grab_frame(self):
        try:
            t = int(round(time.time() * 1000))
            f = self._image_iterator[self.frame]
            if self._frame_time + f.info.get('duration', 0) < t:
                self._frame_time = t
                self.frame += 1
            if self.size is None:
                return f
            else:
                return f.copy().resize(self.size, self.resample)
        except IndexError:
            self.frame = 0
            return self.grab_frame()

    def draw_to(self, im):
        if self.draw:
            f = self.grab_frame().convert("RGBA")
            dp = list(self.position)
            if self.position[0] < 0:
                dp[0] = 0
                f = f.crop((-self.position[0], 0, f.width, f.height))
            if self.position[1] < 0:
                dp[1] = 0
                f = f.crop((0, -self.position[1], f.width, f.height))
            im.alpha_composite(f, tuple(dp))


class Rect(DynamicImage):
    def __init__(self, dimensions, color=(0, 0, 0, 255), position=(0, 0),
                 mode="RGBA", size=None, resample=3):
        self.position = position
        self.size = size
        self.resample = resample
        self.mode = mode
        self.dimensions = dimensions
        self.update_color(color)

    def update_color(self, color, push=True):
        self.color = color
        if push:
            self.update_image(
                Image.new(self.mode, self.dimensions, self.color))


class Text(DynamicImage):

    @classmethod
    def from_truetype(cls, text, path, color=(0, 0, 0),
                      size=16, position=(0, 0)):
        font = _font_cache.setdefault(path + "%" + str(size),
                                      ImageFont.truetype(path, size))
        return cls(text, font, color, size, position)

    def __init__(self, text, font, color=(0, 0, 0), size=16, position=(0, 0)):
        self.position = position
        self.color = color
        self._frame_time = int(round(time.time() * 1000))
        self.update_text(text, font)

    def update_text(self, text, font=None, push=True):
        self.text = text
        if font is not None:
            self._font = font
        if push:
            self.update()

    def update(self):
        size = self._font.getsize(self.text)
        image = Image.new("RGBA", size)
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), self.text, self.color, self._font)
        self.update_image(image)

    def update_color(self, color, push=True):
        self.color = color
        if push:
            self.update()


class SubImage(DynamicImage):
    def __init__(self, dimensions, position=(0, 0), background=(0, 0, 0, 0)):
        self.dimensions = dimensions
        self.position = position
        self.background = background
        self.compositing_order = []

    def grab_frame(self):
        frame = Image.new("RGBA", self.dimensions, self.background)
        for im in self.compositing_order:
            im.draw_to(frame)
        return frame


_fa_root = __file__[:-11] + os.sep \
    + "fonts" + os.sep + "fontawesome-5-free" + os.sep
_fa_b = _fa_root + os.sep + "otfs" + os.sep \
    + "Font Awesome 5 Brands-Regular-400.otf"
_fa_r = _fa_root + os.sep + "otfs" + os.sep \
    + "Font Awesome 5 Free-Regular-400.otf"
_fa_s = _fa_root + os.sep + "otfs" + os.sep \
    + "Font Awesome 5 Free-Solid-900.otf"
_fa_styles = {
    "fab": "brands",
    "far": "regular",
    "fas": "solid"
}
_fa_paths = {
    "brands": _fa_b,
    "regular": _fa_r,
    "solid": _fa_s
}
with open(_fa_root + os.sep + "metadata" + os.sep + "icons.json") as f:
    _fa_meta = json.load(f)

_md_root = __file__[:-11] + os.sep \
    + "fonts" + os.sep + "materialdesign" + os.sep
_md_paths = {  # Used for MDL support later, when(if) there is a ttf
    "regular": _md_root + os.sep + "MaterialDesignIconsDesktop.ttf"
}
with open(_md_root + os.sep + "meta.json") as f:
    _md_meta_raw = json.load(f)
    _md_meta = {}
    for _icon_meta in _md_meta_raw:
        _md_meta[_icon_meta["name"]] = _icon_meta
    del _md_meta_raw
    del _icon_meta

_om_root = __file__[:-11] + os.sep \
    + "fonts" + os.sep + "openmoji" + os.sep
_om_paths = {
    "color": _om_root + os.sep + "OpenMoji-Color.ttf",
    "black": _om_root + os.sep + "OpenMoji-Black.ttf",
}
with open(_om_root + os.sep + "openmoji.json", encoding='utf-8') as f:
    _om_meta_raw = json.load(f)
    _om_meta_annotations = {}
    for _icon_meta in _om_meta_raw:
        _om_meta_annotations[_icon_meta["annotation"]] = _icon_meta
    del _om_meta_raw
    del _icon_meta

_font_cache = {}


def hexchr(char):
    return chr(int(char, 16))


class Icon(Text):

    @classmethod
    def from_fa_str(cls, fa_str, color=(0, 0, 0), size=16,
                    position=(0, 0)):
        '''Create a FontAwesome icon using the string provided on their
        website.'''
        fa_str = fa_str.strip().lower().replace("_", "-")
        style = fa_str[:4].rstrip()
        if style in ("fab", "far", "fas"):
            fa_str = fa_str[4:]
            style = _fa_styles[style]
        else:
            style = None
        if fa_str[:3] == "fa-":
            fa_str = fa_str[3:]
        return cls.from_fa_name(fa_str, style, color, size, position)

    @classmethod
    def from_fa_name(cls, fa_name, style=None, color=(0, 0, 0), size=16,
                     position=(0, 0)):
        '''Create a FontAwesome icon using its name. Specify a style using the
        style parameter. Options are "brands", "regular", "solid" and None(use
        the first available style)'''
        fa_name = fa_name.strip().lower().replace("_", "-")
        icon = _fa_meta[fa_name]
        if style is None:
            style = icon["styles"][0]
        font = _font_cache.setdefault(
            _fa_paths[style] + "%" + str(size),
            ImageFont.truetype(_fa_paths[style], size))
        return cls.from_unicode(icon["unicode"], font, color, size, position)

    @staticmethod
    def get_fa_character(fa_name):
        icon = _fa_meta[fa_name]
        return hexchr(icon["unicode"])

    @classmethod
    def from_md_name(cls, md_name, style=None, color=(0, 0, 0), size=16,
                     position=(0, 0)):
        '''Create a Material Design icon using its name. The style parameter is
        currently unused, but will be used for Material Design Light if/when a
        TTF for it is made'''
        md_name = md_name.strip().lower().replace("_", "-")
        icon = _md_meta[md_name]
        style = "regular"  # override until MDL is available (if it ever is)
        font = _font_cache.setdefault(
            _md_paths[style] + "%" + str(size),
            ImageFont.truetype(_md_paths[style], size))
        return cls.from_unicode(icon["codepoint"], font, color, size, position)

    @staticmethod
    def get_md_character(md_name):
        icon = _md_meta[md_name]
        return hexchr(icon["codepoint"])

    @classmethod
    def from_om_name(cls, om_name, style=None, color=(0, 0, 0), size=16,
                     position=(0, 0)):
        '''Create a OpenMoji emoji using its name (annotation). Specify a style
        using the style parameter. Options are "color", "black" and None(use
        default: black). Do note pillow does not seem to support colored fonts,
        so all emojis will be black line drawings.

        emojis designed by OpenMoji – the open-source emoji and icon project.
        License: CC BY-SA 4.0'''
        icon = _om_meta_annotations[om_name]
        if style is None:
            style = "black"
        font = _font_cache.setdefault(
            _om_paths[style] + "%" + str(size),
            ImageFont.truetype(_om_paths[style], size))
        return cls(icon["emoji"], font, color, size, position)

    @classmethod
    def from_om_icon(cls, om_icon, style=None, color=(0, 0, 0), size=16,
                     position=(0, 0)):
        '''Create a OpenMoji emoji using its icon (actual unicode character).
        Specify a style using the style parameter. Options are "color", "black"
        and None(use default: black). Do note pillow does not seem to support
        colored fonts, so all emojis will be black line drawings.

        emojis designed by OpenMoji – the open-source emoji and icon project.
        License: CC BY-SA 4.0'''
        if style is None:
            style = "black"
        font = _font_cache.setdefault(
            _om_paths[style] + "%" + str(size),
            ImageFont.truetype(_om_paths[style], size))
        return cls(om_icon, font, color, size, position)

    @classmethod
    def from_om_hex(cls, om_hex, style=None, color=(0, 0, 0), size=16,
                    position=(0, 0)):
        '''Create a OpenMoji emoji using its hex (unicode codepoint).
        Specify a style using the style parameter. Options are "color", "black"
        and None(use default: black). Do note pillow does not seem to support
        colored fonts, so all emojis will be black line drawings.

        emojis designed by OpenMoji – the open-source emoji and icon project.
        License: CC BY-SA 4.0'''
        if style is None:
            style = "black"
        font = _font_cache.setdefault(
            _om_paths[style] + "%" + str(size),
            ImageFont.truetype(_om_paths[style], size))
        return cls(hexchr(om_hex), font, color, size, position)

    @staticmethod
    def get_om_character(om_name):
        icon = _om_meta_annotations[om_name]
        return icon["emoji"]

    @classmethod
    def from_unicode(cls, codepoint, font, color=(0, 0, 0), size=16,
                     position=(0, 0)):
        char = hexchr(codepoint)
        return cls(char, font, color, size, position)


class Hotspot:
    '''Base class for hotspot. Can also act as a global hotspot for screen wide
    bindings.'''

    def __init__(self):
        self._bindings = {}
        self.flags = {}

    def add_binding(self, binding, function, invert=False):
        self._bindings[binding] = function

    def get_bindings(self):
        return self._bindings

    def in_area(self, coords):
        return True

    def execute_if_inside(self, binding, coords, invert=False):
        if binding in self._bindings.keys():
            if self.in_area(coords) != invert:
                self.execute(binding, coords)
                return True
        return False

    def execute(self, binding, coords=(0, 0)):
        self._bindings[binding](coords)


class CircleHotspot(Hotspot):
    '''Circular hotspot.'''

    def __init__(self, center, radius, inside=True):
        super().__init__()
        self.center = center
        self.radius = radius
        self.inside = inside

    def in_area(self, coords):
        distances = (self.center[0]-coords[0], self.center[1]-coords[1])
        distance = (distances[0]**2+distances[1]**2)**0.5
        return (distance <= self.radius) == self.inside


class RectangleHotspot(Hotspot):
    '''Rectangular hotspot.'''

    def __init__(self, position, dimensions, inside=True):
        super().__init__()
        self.position = position
        self.dimensions = dimensions
        self.inside = inside

    def in_area(self, coords):
        x_valid = (coords[0] >= self.position[0]) \
            and (coords[0] < self.position[0] + self.dimensions[0])
        y_valid = (coords[1] >= self.position[1]) \
            and (coords[1] < self.position[1] + self.dimensions[1])
        return (x_valid and y_valid) == self.inside
