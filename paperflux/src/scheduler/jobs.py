import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os
from src.services.paper_fetcher import PaperFetcher
from src.services.paper_analyzer import PaperAnalyzer
from src.services.database import DatabaseService
import threading
from concurrent.futures import ThreadPoolExecutor


class PaperProcessingScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.fetcher = PaperFetcher()
        self.analyzer = PaperAnalyzer()
        self.db = DatabaseService()
        self._running = False
        self.paper_processed_event = asyncio.Event()
        self._lock = threading.Lock()
        self.refresh_callbacks = []

    def register_refresh_callback(self, callback):
        """Register a callback to be called when a paper is processed"""
        with self._lock:
            self.refresh_callbacks.append(callback)

    def unregister_refresh_callback(self, callback):
        """Unregister a callback"""
        with self._lock:
            if callback in self.refresh_callbacks:
                self.refresh_callbacks.remove(callback)

    def _notify_refresh(self):
        """Notify all registered callbacks that a paper has been processed"""
        with self._lock:
            callbacks = list(self.refresh_callbacks)

        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in refresh callback: {str(e)}")

    def analyze_and_store_paper(self, paper_entry, pdf_path):
        """Analyze a paper and store it in the database"""
        try:
            explanation = self.analyzer.analyze_paper(pdf_path)
            paper_obj = self.fetcher.parse_paper_data(paper_entry)
            paper_obj.explanation = explanation
            self.db.insert_paper(paper_obj)

            self._notify_refresh()

            return True
        except Exception as e:
            print(f"Error analyzing paper {paper_entry['paper']['id']}: {str(e)}")
            return False
        finally:
            if os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except:
                    pass

    async def process_papers(self):
        if self._running:
            print("Previous processing still running, skipping...")
            return

        self._running = True
        print("Starting daily paper processing...")

        try:
            self.db.clear_collection()
            # Fetch list of all papers
            papers = await self.fetcher.fetch_papers()

            # Download all papers in parallel(BG thread)
            paper_paths = await self.fetcher.download_papers(papers)

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = []

                for paper in papers:
                    paper_id = paper["paper"]["id"]
                    if paper_id in paper_paths:
                        futures.append(
                            executor.submit(
                                self.analyze_and_store_paper,
                                paper,
                                paper_paths[paper_id],
                            )
                        )

                for future in futures:
                    future.result()

        except Exception as e:
            print(f"Error in paper processing: {str(e)}")
        finally:
            self._running = False

    def start(self):
        self.scheduler.add_job(
            lambda: asyncio.run(self.process_papers()),
            "cron",
            hour=0,
            minute=0,
            next_run_time=datetime.now(),
        )
        self.scheduler.start()

    def stop(self):
        self._running = False
        self.scheduler.shutdown()
