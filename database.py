import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

try:  # pragma: no cover - the happy path is exercised in tests
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:  # pragma: no cover - fallback exercised when motor missing
    AsyncIOMotorClient = None  # type: ignore[assignment]

load_dotenv()

logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL")


class _InMemoryCollection:
    """Simple async-friendly stand-in for the Motor collection API."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = query.get("_id")
        return self._store.get(key) if isinstance(key, str) else None

    async def insert_one(self, document: Dict[str, Any]) -> None:
        key = document.get("_id")
        if isinstance(key, str):
            self._store[key] = document


def _fallback_collection(reason: str, *, exc: Exception | None = None):
    if exc:
        logger.warning("%s; using in-memory cache instead", reason, exc_info=exc)
    else:
        logger.warning("%s; using in-memory cache instead", reason)
    return _InMemoryCollection()


def _init_collection():
    """Initialise the Mongo collection when configuration is available."""

    if not MONGO_URL:
        return _fallback_collection("MONGO_URL is not set")

    if AsyncIOMotorClient is None:
        return _fallback_collection("motor is not installed")

    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client.feature_detection
        return db.image_results
    except Exception as exc:  # pragma: no cover - exercised on misconfiguration
        return _fallback_collection("Failed to initialise Mongo client", exc=exc)


collection = _init_collection()


async def get_image_result(image_hash):
    """Retrieve the processing result of an image from storage."""

    return await collection.find_one({"_id": image_hash})


async def save_image_result(image_hash, result):
    """Persist the processing result of an image."""

    document = {"_id": image_hash, "result": result}
    await collection.insert_one(document)
