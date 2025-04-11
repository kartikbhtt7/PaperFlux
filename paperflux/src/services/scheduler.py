import logging
import threading
import time
from datetime import datetime, timedelta
import pytz

from src.services.paper_processor import PaperProcessor
from src.services.database import DatabaseService

logger = logging.getLogger("paperflux.scheduler")

class PaperScheduler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PaperScheduler, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        logger.info("Initializing PaperScheduler")
        self._initialized = True
        self._running = False
        self._thread = None
        self.db_service = DatabaseService()
        self.paper_processor = PaperProcessor()
    
    def start_scheduler(self):
        """Start the paper processing scheduler thread"""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Paper scheduler started")
    
    def _scheduler_loop(self):
        """Main scheduler loop checking for processing time"""
        while self._running:
            try:
                now = datetime.now(pytz.UTC)
                
                # Check if we should process papers
                should_process = self._should_process_now(now)
                
                if should_process:
                    logger.info("Scheduled processing triggered, starting paper processing")
                    # Run the paper processing
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.paper_processor.process_papers())
                    loop.close()
                
                # Sleep for 60 minutes before checking again
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(300)  # Sleep for 5 minute on error before retrying
    
    def _should_process_now(self, current_time):
        """Determine if we should process papers at this time"""
        # Check if processing is already running
        metadata = self.db_service.get_processing_metadata()
        if metadata.is_processing:
            return False
        
        # Get the date of the last processing
        last_date = metadata.last_processed_date.date()
        current_date = current_time.date()
        
        # Only process on weekdays
        if current_time.weekday() >= 5:  # Saturday or Sunday
            return False
            
        # Check if we already processed today
        if last_date == current_date:
            return False
            
        # Check if it's after 8:00 AM UTC
        target_time = datetime.combine(current_date, datetime.min.time(), tzinfo=pytz.UTC)
        target_time = target_time.replace(hour=8, minute=0)
        
        return current_time >= target_time
    
    def stop_scheduler(self):
        """Stop the scheduler thread"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        logger.info("Paper scheduler stopped")