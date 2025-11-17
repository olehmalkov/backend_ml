"""Integration-style tests for the public HTTP handlers in ``app``.

The entire module is self-contained so it can be pasted into another project in
one go, matching the user's requested workflow.
"""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

import pytest

import app
import database


# ---------------------------------------------------------------------------
# Event loop management
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    """Provide a dedicated event loop for this module."""

    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Helpers for resetting state between tests
# ---------------------------------------------------------------------------


def _clear_collection(collection, *, loop: asyncio.AbstractEventLoop) -> None:
    clear = getattr(collection, "clear", None)
    if callable(clear):
        clear()
        return

    delete_many = getattr(collection, "delete_many", None)
    if delete_many is not None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(delete_many({}))


@pytest.fixture(autouse=True)
def _reset_collections(event_loop: asyncio.AbstractEventLoop) -> None:
    for collection in (database.collection, database.logs_collection):
        _clear_collection(collection, loop=event_loop)


# ---------------------------------------------------------------------------
# Detector patching utilities
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _ready_detector(monkeypatch: pytest.MonkeyPatch) -> None:
    app.detector.ready = True

    async def fake_process_image(path: str) -> dict[str, str]:
        with open(path, "rb") as handle:
            payload = handle.read()
        return {"result": f"len={len(payload)}"}

    monkeypatch.setattr(app.detector, "process_image", fake_process_image)


# ---------------------------------------------------------------------------
# Request/field fakes so we do not depend on ``aiohttp`` in tests
# ---------------------------------------------------------------------------


@dataclass
class _FakeField:
    data: bytes
    filename: str = "test.jpg"

    async def read(self) -> bytes:  # pragma: no cover - trivial coroutine
        return self.data


class _FakeMultipartReader:
    def __init__(self, field: _FakeField | None):
        self._field = field
        self._consumed = False

    async def next(self):
        if self._consumed:
            return None
        self._consumed = True
        return self._field


class _FakeRequest:
    def __init__(self, field: _FakeField | None):
        self._reader = _FakeMultipartReader(field)

    async def multipart(self) -> _FakeMultipartReader:  # pragma: no cover
        return self._reader


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _run(loop: asyncio.AbstractEventLoop, coro):
    return loop.run_until_complete(coro)


def _get_logs(filter_query: dict[str, object], *, loop):
    return _run(loop, database.get_logs(filter_query))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_app_imports() -> None:
    """Basic smoke test that the application module loads correctly."""

    module = importlib.import_module("app")
    assert hasattr(module, "check_status")
    assert hasattr(module, "process_image")


def test_process_image_logs_cache_reuse(event_loop: asyncio.AbstractEventLoop) -> None:
    """Repeated uploads should log cache reuse in the request log."""

    image_bytes = b"test-image-contents"

    for _ in range(2):
        request = _FakeRequest(_FakeField(image_bytes))
        response = _run(event_loop, app.process_image(request))
        assert response.status == 200
        payload = _run(event_loop, response.json())
        assert payload["result"].startswith("len=")

    logs = _get_logs({"endpoint": "process-image"}, loop=event_loop)
    assert len(logs) == 2
    assert [log["cache_reused"] for log in logs] == [False, True]
    assert all(isinstance(log["timestamp"], datetime) for log in logs)
    assert logs[0]["image_hash"] == logs[1]["image_hash"]


def test_check_status_logging(event_loop: asyncio.AbstractEventLoop) -> None:
    """GET /check-status should record a log entry."""

    response = _run(event_loop, app.check_status(object()))
    assert response.status == 200
    payload = _run(event_loop, response.json())
    assert payload == {"status": "ready"}

    logs = _get_logs({"endpoint": "check-status"}, loop=event_loop)
    assert len(logs) == 1
    entry = logs[0]
    assert entry["cache_reused"] is False
    assert entry["image_hash"] is None
    assert isinstance(entry["timestamp"], datetime)
