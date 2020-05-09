import digitalio
import board
from gpiozero import Button

# import adafruit_rgb_display.ili9341 as ili9341
# import adafruit_rgb_display.st7789 as st7789
# import adafruit_rgb_display.hx8357 as hx8357
# import adafruit_rgb_display.st7735 as st7735
import adafruit_rgb_display.ssd1351 as ssd1351
# import adafruit_rgb_display.ssd1331 as ssd1331

cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)
BAUDRATE = 24000000
spi = board.SPI()

services = {}
plugin = {}
core = None
gui_core = None
run_thread = None
thread_active = False
screen = None
screen_size = (128*4, 128*4)
render_size = (128*4, 128*4)
disp = None
_window_name = "pi_gui_display_adafruit"


def _register_(serviceList, pluginProperties):
    global services, plugin, core, gui_core
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    gui_core = services["gui_core"][0]


buttons = []


def setup():
    global render_size, screen_size
    setup_ssd1351_150()
    if disp.rotation % 180 == 90:
        height = disp.width
        width = disp.height
    else:
        width = disp.width
        height = disp.height
    screen_size = render_size = (width, height)
    gui_core.prepare(render_size)

    buttons.append(Button(4, pull_up=None, active_state=True))
    buttons[-1].when_pressed = lambda x: gui_core.trigger((0, 0), "action:toggle_menu")
    buttons.append(Button(17, pull_up=None, active_state=True))
    buttons[-1].when_pressed = lambda x: gui_core.trigger((0, 0), "action:menu_up")
    buttons.append(Button(23, pull_up=None, active_state=True))
    buttons[-1].when_pressed = lambda x: gui_core.trigger((0, 0), "action:menu_down")
    buttons.append(Button(27, pull_up=None, active_state=True))
    buttons[-1].when_pressed = lambda x: gui_core.trigger((0, 0), "action:menu_select")
    buttons.append(Button(20, pull_up=None, active_state=True))
    buttons[-1].when_pressed = lambda x: gui_core.trigger((0, 0), "action:increment_tab")
    buttons.append(Button(16, pull_up=None, active_state=True))
    buttons[-1].when_pressed = lambda x: gui_core.trigger((0, 0), "action:decrement_tab")
    print(buttons)

    return render_size


def set_name(name):
    global screen, _window_name
    _window_name = name


def scale_event(position):
    x = int(position[0] / screen_size[0] * render_size[0])
    y = int(position[1] / screen_size[1] * render_size[1])
    return (x, y)


sc = 0


def draw():
    frame_pil = gui_core.get_frame().resize(screen_size, 0)
    disp.image(frame_pil)


def setup_ssd1351_150():
    global disp
    disp = ssd1351.SSD1351(spi, rotation=180,
                           cs=cs_pin, dc=dc_pin, rst=reset_pin,
                           baudrate=BAUDRATE)
