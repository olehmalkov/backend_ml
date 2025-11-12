"""Basic tests for the feature detection service.

These tests import the application modules to verify that they load correctly.
They can be extended with more comprehensive integration tests using
`pytest-aiohttp` or other frameworks.
"""


def test_app_imports():
    """Ensure that the main application module can be imported without errors."""
    import importlib

    module = importlib.import_module("app")
    # The application exposes two coroutine handlers that should exist
    assert hasattr(module, "check_status")
    assert hasattr(module, "process_image")