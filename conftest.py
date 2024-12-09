import pytest

pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function" 