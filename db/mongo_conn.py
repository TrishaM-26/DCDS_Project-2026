import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
# Temporary bypass for local testing behind strict networks
_client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)

# Initialize client with certifi handling the SSL certificate
_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = _client[MONGO_DB]

def get_collection(name):
    return db[name]