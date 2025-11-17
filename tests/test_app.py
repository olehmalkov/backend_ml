"""Tests for the feature detection service HTTP handlers."""

import importlib
from datetime import datetime
from typing import AsyncIterator

import pytest
import pytest_asyncio
from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer

import app
import database


async def test_app_imports():
    """Ensure that the main application module can be imported without errors."""

    module = importlib.import_module("app")
    assert hasattr(module, "check_status")
    assert hasattr(module, "process_image")


@pytest.fixture(autouse=True)
async def _reset_collections():
    """Clear collections between tests."""
    if isinstance(database.collection, dict):
        database.collection.clear()
    else:
        await database.collection.delete_many({})


@pytest_asyncio.fixture
async def client(monkeypatch) -> AsyncIterator[TestClient]:
    """Provide a test client with a ready detector."""

    app.detector.ready = True

    async def fake_process_image(path: str):
        return {"result": "processed"}

    monkeypatch.setattr(app.detector, "process_image", fake_process_image)

    application = web.Application()
    application.router.add_get("/check-status", app.check_status)
    application.router.add_post("/process-image", app.process_image)

    server = TestServer(application)
    test_client = TestClient(server)
    await test_client.start_server()

    try:
        yield test_client
    finally:
        await test_client.close()


@pytest.mark.asyncio
async def test_process_image_logs_cache_reuse(client):
    """Repeated requests for the same image should log cache usage."""

    image_bytes = b"test-image-contents"

    form = FormData()
    form.add_field("file", image_bytes, filename="test.jpg", content_type="image/jpeg")
    response = await client.post("/process-image", data=form)
    assert response.status == 200
    await response.json()

    form = FormData()
    form.add_field("file", image_bytes, filename="test.jpg", content_type="image/jpeg")
    response = await client.post("/process-image", data=form)
    assert response.status == 200
    await response.json()

    logs = await database.get_logs({"endpoint": "process-image"})
    assert len(logs) == 2
    assert [log["cache_reused"] for log in logs] == [False, True]
    assert all(isinstance(log["timestamp"], datetime) for log in logs)
    assert logs[0]["image_hash"] == logs[1]["image_hash"]


@pytest.mark.asyncio
async def test_check_status_logging(client):
    """Status checks should be recorded in the request log."""

    response = await client.get("/check-status")
    assert response.status == 200
    payload = await response.json()
    assert payload == {"status": "ready"}

    logs = await database.get_logs({"endpoint": "check-status"})
    assert len(logs) == 1
    entry = logs[0]
    assert entry["cache_reused"] is False
    assert entry["image_hash"] is None
    assert isinstance(entry["timestamp"], datetime)
