"""
MongoDB Connection Management

Provides async MongoDB client using motor.
"""
import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from .config import config


class MongoDB:
    """Singleton MongoDB connection manager."""
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize MongoDB connection and create indexes."""
        if cls.client is not None:
            return

        try:
            cls.client = AsyncIOMotorClient(
                config.mongodb_url,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=1,
            )
            cls.db = cls.client[config.mongodb_db]

            # Verify connection
            await cls.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {config.mongodb_db} at {config.mongodb_url}")

            # Create indexes for feedback queries
            await cls._create_indexes()
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def _create_indexes(cls) -> None:
        """Create indexes for optimal query performance."""
        logs_collection = cls.db.logs if cls.db else None
        if logs_collection is not None:
            try:
                # Index on messageId for fast feedback lookups (unique for upsert)
                await logs_collection.create_index("messageId", unique=True)
                # Index on serverId for filtering feedback by MCP server
                await logs_collection.create_index("serverId")
                # Index on timestamp for potential sorting/analytics
                await logs_collection.create_index("timestamp")
                print("✅ Created MongoDB indexes for logs collection")
            except Exception as e:
                print(f"⚠️ Index creation warning: {e}")

    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            print("✅ MongoDB connection closed")

    @classmethod
    def get_database(cls):
        """Get database instance."""
        if cls.db is None:
            raise RuntimeError("MongoDB not initialized. Call connect() first.")
        return cls.db

    @classmethod
    def get_collection(cls, collection_name: str):
        """Get a collection by name."""
        db = cls.get_database()
        return db[collection_name]


# Convenience function to get logs collection
async def get_logs_collection():
    """Get the chat logs collection with proper initialization."""
    await MongoDB.connect()
    return MongoDB.get_collection("chat_logs")
