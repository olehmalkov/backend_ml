import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

client = AsyncIOMotorClient(MONGO_URL)
db = client.feature_detection
collection = db.image_results

async def get_image_result(image_hash):
    """
    Retrieves the processing result of an image from the database.
    """
    return await collection.find_one({"_id": image_hash})

async def save_image_result(image_hash, result):
    """
    Saves the processing result of an image to the database.
    """
    await collection.insert_one({"_id": image_hash, "result": result})
