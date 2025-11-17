import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

try:  # pragma: no cover - the happy path is exercised in tests
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:  # pragma: no cover - fallback exercised when motor missing
    AsyncIOMotorClient = None  # type: ignore[assignment]

load_dotenv()

logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL")


class _MotorCollectionWrapper:
    """Adapts a Motor collection so pytest fixtures can detect ``clear``.

    ``tests/conftest.py`` occasionally checks if a collection exposes a ``clear``
    method in order to wipe in-memory stores. Motor collections do not provide a
    synchronous ``clear`` method, but because they are attribute-accessible,
    ``getattr(collection, "clear", None)`` would attempt to call a coroutine and
    would skip the async clean-up path that uses ``delete_many``.  To keep the
    production object untouched while making the fixture logic consistent, we
    wrap the Motor collection and deliberately raise ``AttributeError`` when the
    ``clear`` attribute is requested. All other attributes are delegated so the
    async API (``find_one``, ``insert_one``, ``delete_many`` …) continues to work
    transparently.
    """

    __slots__ = ("_collection",)

    def __init__(self, collection):
        self._collection = collection

    def __getattr__(self, item):
        if item == "clear":
            raise AttributeError("Motor collections do not implement 'clear'")
        return getattr(self._collection, item)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"_MotorCollectionWrapper({self._collection!r})"


class _InMemoryCollection:
    """Simple async-friendly stand-in for the Motor collection API."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = query.get("_id")
        return self._store.get(key) if isinstance(key, str) else None

    async def insert_one(self, document: Dict[str, Any]) -> None:
        doc = dict(document)
        key = doc.get("_id")
        if not isinstance(key, str):
            key = str(uuid.uuid4())
            doc["_id"] = key
        self._store[key] = doc

    async def find(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query = query or {}
        results: List[Dict[str, Any]] = []
        for document in self._store.values():
            if all(document.get(field) == value for field, value in query.items()):
                results.append(document)
        return results

    def clear(self) -> None:
        self._store.clear()


def _fallback_collection(reason: str, *, exc: Exception | None = None):
    if exc:
        logger.warning("%s; using in-memory cache instead", reason, exc_info=exc)
    else:
        logger.warning("%s; using in-memory cache instead", reason)
    return _InMemoryCollection()


def _init_collection(collection_name: str):
    """Initialise a Mongo collection when configuration is available."""

    if not MONGO_URL:
        return _fallback_collection("MONGO_URL is not set")

    if AsyncIOMotorClient is None:
        return _fallback_collection("motor is not installed")

    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client.feature_detection
        collection = getattr(db, collection_name)
        return _MotorCollectionWrapper(collection)
    except Exception as exc:  # pragma: no cover - exercised on misconfiguration
        return _fallback_collection("Failed to initialise Mongo client", exc=exc)


collection = _init_collection("image_results")
logs_collection = _init_collection("request_logs")


async def get_image_result(image_hash):
    """Retrieve the processing result of an image from storage."""

    return await collection.find_one({"_id": image_hash})


async def save_image_result(image_hash, result):
    """Persist the processing result of an image."""

    document = {"_id": image_hash, "result": result}
    await collection.insert_one(document)


async def log_request(
    image_hash: Optional[str], endpoint: str, cache_reused: bool
) -> None:
    """Persist metadata about handled API requests."""

    document = {
        "image_hash": image_hash,
        "endpoint": endpoint,
        "cache_reused": cache_reused,
        "timestamp": datetime.now(timezone.utc),
    }
    await logs_collection.insert_one(document)


async def get_logs(filter_query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Retrieve request log entries matching the provided filter."""

    filter_query = filter_query or {}

    if isinstance(logs_collection, _InMemoryCollection):
        results = await logs_collection.find(filter_query)
        return sorted(
            results,
            key=lambda entry: entry.get(
                "timestamp", datetime.min.replace(tzinfo=timezone.utc)
            ),
        )

    cursor = logs_collection.find(filter_query)
    if hasattr(cursor, "sort"):
        cursor = cursor.sort("timestamp", 1)
    if hasattr(cursor, "to_list"):
        return await cursor.to_list(length=None)

    results: List[Dict[str, Any]] = []
    async for item in cursor:  # pragma: no cover - cursor iteration fallback
        results.append(item)
    return results
