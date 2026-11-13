from pymongo import MongoClient, ASCENDING, DESCENDING
from app.config import get_settings

_client = None


def connect():
    global _client
    settings = get_settings()
    if not settings.mongodb_uri:
        raise RuntimeError("MONGODB_URI is missing")
    _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=10000)
    _client.admin.command("ping")
    db = _client[settings.mongodb_database]
    db.users.create_index("email", unique=True)
    db.conversations.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.oauth_codes.create_index("expires_at", expireAfterSeconds=0)
    return db


def get_db():
    if _client is None:
        raise RuntimeError("Database is not connected")
    return _client[get_settings().mongodb_database]


def disconnect():
    global _client
    if _client is not None:
        _client.close()
        _client = None
