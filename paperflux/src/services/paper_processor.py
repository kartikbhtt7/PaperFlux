import os
import logging
from concurrent.futures import ThreadPoolExecutor
from src.services.paper_fetcher import PaperFetcher
from src.services.paper_analyzer import PaperAnalyzer
from src.services.database import DatabaseService

logger = logging.getLogger("paperflux.paper_processor")

class PaperProcessor:
    def __init__(self):
        logger.info("Initializing PaperProcessor")
        self.fetcher = PaperFetcher()
        self.analyzer = PaperAnalyzer()
        self.db = DatabaseService()
        self._running = False
        
    def analyze_and_store_paper(self, paper_entry, pdf_path):
        """Analyze a paper and store it in the database"""
        paper_id = paper_entry["paper"]["id"]
        
        try:
            logger.info(f"Analyzing paper {paper_id}")
            explanation = self.analyzer.analyze_paper(pdf_path)
            
            logger.info(f"Creating paper object for {paper_id}")
            paper_obj = self.fetcher.parse_paper_data(paper_entry)
            paper_obj.explanation = explanation
            
            logger.info(f"Storing paper {paper_id} in database")
            self.db.insert_paper(paper_obj)

            return True
            
        except Exception as e:
            logger.error(f"Error analyzing paper {paper_id}: {str(e)}")
            return False
            
        finally:
            # Clean up
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                    logger.debug(f"Removed temporary file: {pdf_path}")
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {pdf_path}: {str(e)}")

    async def process_papers(self):
        """Process all daily papers"""
        if self._running:
            logger.warning("Previous processing still running, skipping...")
            return False

        self._running = True
        self.db.set_processing_status(True)
        
        logger.info("Starting paper processing...")

        try:
            # Clear existing papers
            self.db.clear_papers_collection()
            
            # Fetch list of all papers
            papers = await self.fetcher.fetch_papers()
            logger.info(f"Fetched {len(papers)} papers, downloading PDFs...")

            # Download all papers in parallel
            paper_paths = await self.fetcher.download_papers(papers)
            logger.info(f"Successfully downloaded {len(paper_paths)} out of {len(papers)} papers")

            # Configure thread pool based on number of available API keys
            api_key_count = len(self.analyzer.api_keys)
            max_workers = min(api_key_count, 10)
            
            logger.info(f"Starting analysis with {max_workers} workers")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
                    else:
                        logger.warning(f"Skipping paper {paper_id} - PDF download failed")

                processed_count = 0
                for future in futures:
                    if future.result():
                        processed_count += 1
                
                logger.info(f"Successfully processed {processed_count} out of {len(futures)} papers")
                    
            # Update last processed date
            self.db.update_last_processed_date()
            logger.info("Paper processing completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error in paper processing: {str(e)}")
            return False
            
        finally:
            self._running = False
            self.db.set_processing_status(False)
