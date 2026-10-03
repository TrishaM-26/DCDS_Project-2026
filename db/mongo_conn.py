from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB

# Created ONCE when the module is first imported, then reused everywhere.
_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
_db = _client[MONGO_DB]

def get_collection(name):
    """Return a collection, e.g. get_collection('waste_logs')."""
    return _db[name]