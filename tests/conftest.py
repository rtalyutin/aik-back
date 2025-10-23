import asyncio
import inspect


def pytest_addoption(parser):
    parser.addini("asyncio_mode", "Asyncio mode (stub for pytest-asyncio compatibility)", default="auto")


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as requiring asyncio support")


def pytest_pyfunc_call(pyfuncitem):
    plugin_manager = pyfuncitem.config.pluginmanager
    if plugin_manager.hasplugin("asyncio"):
        return None

    if inspect.iscoroutinefunction(pyfuncitem.obj):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(pyfuncitem.obj(**pyfuncitem.funcargs))
        finally:
            loop.close()
        return True

    return None
