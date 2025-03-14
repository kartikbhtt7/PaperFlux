import time
from datetime import datetime, timedelta
from pymongo import MongoClient
from src.models.models import Paper, ProcessingMetadata
import threading
import logging
import os
from src.config.settings import DB_NAME, COLLECTION_NAME, METADATA_COLLECTION
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("paperflux.database")

class DatabaseService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        logger.info("Initializing DatabaseService")
        self.client = MongoClient(os.environ["MONGODB_URI"])
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        self.metadata_collection = self.db[METADATA_COLLECTION]
        self._cache = {}
        self._cache_timestamp = 0
        self._cache_lock = threading.Lock()
        self._initialized = True

    def clear_papers_collection(self):
        """Clear the papers collection"""
        logger.info("Clearing papers collection")
        self.collection.delete_many({})
        with self._cache_lock:
            self._cache = {}
            self._cache_timestamp = 0

    def insert_paper(self, paper: Paper):
        """Insert a paper into the database"""
        logger.info(f"Inserting paper: {paper.paper_id}")
        result = self.collection.insert_one(paper.to_dict())
        # Invalidate cache
        with self._cache_lock:
            self._cache = {}
            self._cache_timestamp = 0
        return result

    def get_all_papers(self, max_cache_age_seconds=20):
        """Get all papers, with caching for better performance"""
        current_time = time.time()

        # Check cache validity
        with self._cache_lock:
            if (
                self._cache
                and current_time - self._cache_timestamp <= max_cache_age_seconds
            ):
                return self._cache.get("all_papers", [])

        # Cache miss
        logger.debug("Cache miss for all_papers, fetching from database")
        papers = list(self.collection.find())

        # Update cache
        with self._cache_lock:
            self._cache["all_papers"] = papers
            self._cache_timestamp = current_time

        return papers

    def get_paper_by_id(self, paper_id: str):
        """Get a paper by ID with caching"""
        with self._cache_lock:
            if "all_papers" in self._cache:
                for paper in self._cache["all_papers"]:
                    if paper["paper_id"] == paper_id:
                        return paper
        
        # Cache miss
        return self.collection.find_one({"paper_id": paper_id})

    def get_papers_count(self):
        """Get the count of papers in the database"""
        return self.collection.count_documents({})

    def update_last_processed_date(self):
        """Update the last processed date to now"""
        now = datetime.now()
        logger.info(f"Updating last processed date to {now}")
        
        # Update or insert the processing metadata
        self.metadata_collection.update_one(
            {"_id": "processing_metadata"},
            {"$set": {"last_processed_date": now, "is_processing": False}},
            upsert=True
        )

    def set_processing_status(self, is_processing: bool):
        """Set the processing status"""
        logger.info(f"Setting processing status to {is_processing}")
        self.metadata_collection.update_one(
            {"_id": "processing_metadata"},
            {"$set": {"is_processing": is_processing}},
            upsert=True
        )

    def get_processing_metadata(self) -> ProcessingMetadata:
        """Get the processing metadata"""
        data = self.metadata_collection.find_one({"_id": "processing_metadata"})
        
        if not data:
            # No metadata exists yet
            return ProcessingMetadata()
        
        metadata = ProcessingMetadata()
        metadata.last_processed_date = data.get("last_processed_date", datetime.utcnow())
        metadata.is_processing = data.get("is_processing", False)
        
        return metadata

    def should_process_today(self) -> bool:
        """Check if papers should be processed today based on last processed date"""
        metadata = self.get_processing_metadata()
        
        # If already processing, don't start another process
        if metadata.is_processing:
            logger.info("Paper processing is already running")
            return False
            
        # Get the date (not time) of the last processing
        last_date = metadata.last_processed_date.date()
        today = datetime.utcnow().date()
        
        # If we haven't processed today, or if we have no papers, we should process
        papers_count = self.get_papers_count()
        should_process = (last_date < today) or (papers_count == 0)
        
        # Manual trigger by user, need a fix
        if should_process:
            logger.info(f"Should process papers. Last processed: {last_date}, Today: {today}, Papers count: {papers_count}")
        else:
            logger.info(f"No need to process papers. Last processed: {last_date}, Today: {today}")
            
        return should_process