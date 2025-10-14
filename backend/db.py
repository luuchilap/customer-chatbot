import logging
from typing import Tuple
from pymongo import MongoClient


logger = logging.getLogger(__name__)


def initialize_mongodb(mongo_uri: str, database_name: str) -> Tuple[MongoClient, object]:
    """Create a Mongo client and return (client, database) after a health check.

    The caller is responsible for closing the client.
    """
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    db = client[database_name]
    # Health check
    client.admin.command("ping")
    logger.info("MongoDB connection successful")
    return client, db


