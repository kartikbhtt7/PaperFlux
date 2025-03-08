import time
from pymongo import MongoClient
from src.config.settings import MONGODB_URI, DB_NAME, COLLECTION_NAME
from src.models.models import Paper
import threading


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
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        self._cache = {}
        self._cache_timestamp = 0
        self._cache_lock = threading.Lock()
        self._initialized = True

    def clear_collection(self):
        self.collection.delete_many({})
        with self._cache_lock:
            self._cache = {}
            self._cache_timestamp = 0

    def insert_paper(self, paper: Paper):
        result = self.collection.insert_one(paper.to_dict())
        # Invalidate cache
        with self._cache_lock:
            self._cache = {}
            self._cache_timestamp = 0
        return result

    def get_all_papers(self, max_cache_age_seconds=10):
        """Get all papers, with caching for better performance"""
        current_time = time.time()

        # check cache validity
        with self._cache_lock:
            if (
                self._cache
                and current_time - self._cache_timestamp <= max_cache_age_seconds
            ):
                return self._cache.get("all_papers", [])

        # cache miss
        papers = list(self.collection.find())

        # update cache
        with self._cache_lock:
            self._cache["all_papers"] = papers
            self._cache_timestamp = current_time

        return papers

    def get_paper_by_id(self, paper_id: str):
        """Get a paper by ID with caching"""
        with self._cache_lock:
            if "all_papers" in self._cache:
                for paper in self._cache["all_papers"]:
                    if paper["id"] == paper_id:
                        return paper
        # cache miss
        return self.collection.find_one({"id": paper_id})
