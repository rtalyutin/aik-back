from __future__ import annotations

import asyncio
import inspect

from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.python import Function


def pytest_addoption(parser: Parser) -> None:
    parser.addini(
        "asyncio_mode",
        "Asyncio mode (stub for pytest-asyncio compatibility)",
        default="auto",
    )


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers", "asyncio: mark test as requiring asyncio support"
    )


def pytest_pyfunc_call(pyfuncitem: Function) -> bool | None:
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
