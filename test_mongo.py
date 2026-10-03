from db.mongo_conn import _client

try:
    _client.admin.command("ping")
    print("Connected to MongoDB Atlas")
except Exception as e:
    print(f"Connection failed: {e}")