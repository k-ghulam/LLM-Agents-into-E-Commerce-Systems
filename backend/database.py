"""
Database configuration and MongoDB connection setup.

Importing this module performs no network I/O: ``MongoClient`` connects lazily,
and the unique-account indexes are created by :func:`ensure_indexes`, which the
app calls once on startup from its lifespan handler. This keeps the test suite
fully offline (the tests swap these collections for in-memory fakes).
"""
from pymongo import MongoClient

from .config import settings

MONGO_URI = settings.mongo_uri

# MongoClient does not connect until the first operation, so this is import-safe.
client = MongoClient(MONGO_URI or "mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
db = client["ecommerce_db"]

users_collection = db["users"]
products_collection = db["products"]
orders_collection = db["orders"]
cart_collection = db["cart"]
wishlist_collection = db["wishlist"]


def ensure_indexes() -> None:
    """
    Create the unique indexes that enforce one account per email and per
    username at the database level. Idempotent — safe to call on every startup.
    """
    wishlist_collection.create_index("user_id", unique=True)
    products_collection.create_index([("category", 1), ("price_cents", 1)])
    users_collection.create_index("email", unique=True)
    users_collection.create_index("username", unique=True, name="accounts_username_ci", collation={"locale": "en", "strength": 2})
    sessions_collection.create_index("token_hash", unique=True)
    sessions_collection.create_index("expires_at", expireAfterSeconds=0)
    rate_limits_collection.create_index("expires_at", expireAfterSeconds=0)
    cart_collection.create_index([("user_email", 1), ("product_name", 1)], unique=True)
    orders_collection.create_index([("user_email", 1), ("created_at", -1)])

# Store only digests of random session tokens. MongoDB TTL removes expired rows;
# authentication also checks expiry, since TTL cleanup is asynchronous.
sessions_collection = db["sessions"]
rate_limits_collection = db["rate_limits"]
