from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import  OperationFailure , DuplicateKeyError
from src.core.config import settings
from src.core.logger import logger

class MongoManager:
    """
    A Singleton-like or Instance-based wrapper for MongoDB operations.
    Handles connection, writing (insert), and reading (find).
    """
    def __init__(self, collection_name: str | None = None):
        try:
            self.client = AsyncIOMotorClient(settings.mongo_uri)
            self.db = self.client[settings.mongo_db_name]
            self.collection = self.db[collection_name or settings.mongo_collection_name]
            logger.info("✅ MongoDB Client Initialized")
        except Exception as e:
            logger.critical(f"❌ Failed to initialize MongoDB Client: {e}", exc_info=True)
            raise

    async def write_data(self, document: dict) -> str:
        """
        Tries to insert a new document. 
        Returns None if ID already exists.
        """
        try:
            result = await self.collection.insert_one(document)
            logger.info(f"💾 Document saved successfully with ID: {result.inserted_id}")
            return str(result.inserted_id)
        
        except DuplicateKeyError:
            # This block runs if the ID already exists
            logger.error(f"⛔ Duplicate ID detected: {document.get('_id')}. Insert skipped.")
            return None
            
        except OperationFailure as e:
            logger.error(f"❌ MongoDB Operation failed during write: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error writing to MongoDB: {e}", exc_info=True)
            return None

    async def upsert_data(self, document: dict) -> str:
        """
        Smart Save: 
        - If ID exists -> Overwrites the old data (Update).
        - If ID does not exist -> Creates new data (Insert).
        """
        try:
            # Ensure the document has an _id field
            if '_id' not in document:
                logger.error("❌ Cannot upsert document without '_id' field.")
                return None

            doc_id = document['_id']
            
            # replace_one with upsert=True
            result = await self.collection.replace_one(
                filter={'_id': doc_id}, 
                replacement=document, 
                upsert=True
            )
            
            if result.matched_count > 0:
                logger.info(f"🔄 Updated existing document with ID: {doc_id}")
            else:
                logger.info(f"💾 Inserted new document with ID: {doc_id}")
                
            return str(doc_id)

        except Exception as e:
            logger.error(f"❌ Error during upsert: {e}", exc_info=True)
            return None

    async def read_data(self, query: dict, limit: int = 1, sort: list[tuple[str, int]] | None = None):
        """
        Reads data based on a query filter. 
        If limit is 1, returns a single dict. Otherwise returns a list.
        """
        try:
            if limit == 1:
                document = await self.collection.find_one(query, sort=sort)
                return document
            else:
                cursor = self.collection.find(query)
                if sort:
                    cursor = cursor.sort(sort)
                cursor = cursor.limit(limit)
                documents = await cursor.to_list(length=limit)
                return documents
        except OperationFailure as e:
            logger.error(f"❌ MongoDB Operation failed during read: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error reading from MongoDB: {e}", exc_info=True)
            return None

    def close(self):
        self.client.close()
        logger.info("🔒 MongoDB Connection Closed")
