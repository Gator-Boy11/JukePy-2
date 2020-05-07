import threading

services = {}
plugin = {}
core = None
run_thread = None
thread_active = False


def _register_(serviceList, pluginProperties):
    global services, plugin, core
    services = serviceList
    plugin = pluginProperties
    core = services["core"][0]
    # core.add_start(start_thread)
    # core.add_close(close_thread)
    # core.add_loop(loop_task)


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
