import threading
import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

services = {}
plugin = {}
core = None
gui_core = None
run_thread = None
thread_active = False
screen = None
screen_size = (128*4, 128*4)
render_size = (128*4, 128*4)
_window_name = "pi_gui_display_pygame"
_fps = 60
clock = None


def _register_(serviceList, pluginProperties):
    global services, plugin, core, gui_core
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    gui_core = services["gui_core"][0]
    # core.addStart(start_thread)
    # core.addClose(close_thread)
    # core.addStart(setup)
    # core.addLoop(loop_task)


def setup():
    global screen, clock
    pygame.init()
    pygame.display.set_caption(_window_name)
    screen = pygame.display.set_mode(screen_size)
    gui_core.prepare(render_size)
    clock = pygame.time.Clock()
    return render_size


def set_name(name):
    global screen, _window_name
    pygame.display.set_caption(name)
    _window_name = name


def scale_event(position):
    x = int(position[0] / screen_size[0] * render_size[0])
    y = int(position[1] / screen_size[1] * render_size[1])
    return (x, y)

sc = 0

def draw():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            core.stop()
            return
        elif event.type == pygame.MOUSEMOTION:
            gui_core.hover(scale_event(event.pos))
        elif event.type == pygame.MOUSEBUTTONUP:
            gui_core.mouse_up(scale_event(event.pos), event.button)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            gui_core.mouse_down(scale_event(event.pos), event.button)
        elif event.type == pygame.KEYDOWN:
            # print(f"key:down:{event.key}")
            gui_core.trigger((0, 0), f"key:down:{event.key}")
        elif event.type == pygame.KEYUP:
            # print(f"key:up:{event.key}")
            gui_core.trigger((0, 0), f"key:up:{event.key}")
        else:
            pass  # print(event.type)
    frame_pil = gui_core.get_frame().resize(screen_size, 0)
    frame_mode = frame_pil.mode
    frame_size = frame_pil.size
    frame_data = frame_pil.tobytes()
    frame_surface = pygame.image.fromstring(frame_data, frame_size, frame_mode)
    screen.blit(frame_surface, (0, 0))
    pygame.display.flip()
    if _fps < 0:
        clock.tick_busy_loop(-1*_fps)
    else:
        clock.tick(_fps)
    # print(clock.get_fps())


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
