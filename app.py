import asyncio
import hashlib
import logging
import os
from typing import Optional
from aiohttp import web
from feature_detector import FeatureDetector
import database

# Configure a basic logger. In containerised deployments logs are written to
# stdout/stderr so they can be captured by the orchestrator.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Instantiate a global FeatureDetector. It will start warming up on service startup.
detector = FeatureDetector()

async def check_status(request):
    """
    Returns the service's readiness status.
    """
    if detector.ready:
        await database.log_request(None, "check-status", cache_reused=False)
        return web.json_response({"status": "ready"})
    else:
        # Emit a debug log when the service is queried before it is ready
        logger.debug("Received status check while still warming up")
        await database.log_request(None, "check-status", cache_reused=False)
        return web.json_response({"status": "warming up"}, status=503)

async def process_image(request):
    """
    Processes an image file, using a database to cache results.
    """
    if not detector.ready:
        await database.log_request(None, "process-image", cache_reused=False)
        return web.json_response({"error": "Service not ready"}, status=503)

    reader = await request.multipart()
    field = await reader.next()
    if not field:
        await database.log_request(None, "process-image", cache_reused=False)
        return web.json_response({"error": "No image file provided"}, status=400)

    image_hash: Optional[str] = None
    image_data = await field.read()
    image_hash = hashlib.sha256(image_data).hexdigest()

    # Check for cached result
    cached_result = await database.get_image_result(image_hash)
    if cached_result:
        await database.log_request(image_hash, "process-image", cache_reused=True)
        return web.json_response(cached_result["result"])

    # Save image to a temporary file. Use a deterministic name derived from the
    # incoming filename to aid debugging; in production consider using tempfile.
    filename = field.filename
    temp_image_path = f"/tmp/{filename}"
    with open(temp_image_path, "wb") as f:
        f.write(image_data)

    try:
        # Process the image
        result = await detector.process_image(temp_image_path)
        # Save result to database
        await database.save_image_result(image_hash, result)
        await database.log_request(image_hash, "process-image", cache_reused=False)
        return web.json_response(result)
    except Exception as e:
        await database.log_request(image_hash, "process-image", cache_reused=False)
        return web.json_response({"error": str(e)}, status=500)
    finally:
        os.remove(temp_image_path)

async def main():
    """
    Main function to start the service.
    """
    app = web.Application()
    app.router.add_get("/check-status", check_status)
    app.router.add_post("/process-image", process_image)

    # Run warmup in the background
    asyncio.create_task(detector.warmup())

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5000)
    await site.start()
    print("Server started at http://0.0.0.0:5000")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
