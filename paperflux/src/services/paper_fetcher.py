import os
import aiohttp
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from src.config.settings import HF_API_URL, PDF_BASE_URL, TEMP_DIR
from src.models.models import Paper

logger = logging.getLogger("paperflux.paper_fetcher")

class PaperFetcher:
    def __init__(self):
        os.makedirs(TEMP_DIR, exist_ok=True)
        logger.info(f"PaperFetcher initialized with temp directory: {TEMP_DIR}")

    async def fetch_papers(self) -> List[dict]:
        """Fetch daily papers from the Hugging Face API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(HF_API_URL) as response:
                if response.status == 200:
                    papers = await response.json()
                    logger.info(f"Found {len(papers)} papers from Hugging Face API")
                    return papers
                error_msg = f"API request failed: {response.status}"
                logger.error(error_msg)
                raise Exception(error_msg)

    async def download_paper(self, paper_entry: dict) -> Optional[str]:
        """
        Download a single paper's PDF.
        Returns the path to the downloaded PDF or None if download failed.
        """
        try:
            paper_id = paper_entry["paper"]["id"]
            pdf_url = PDF_BASE_URL.format(id=paper_id)
            # Clean ID for safe filename
            clean_id = paper_id.replace("/", "_").replace(":", "_")
            filename = f"{datetime.now().date()}_{clean_id}.pdf"
            filepath = os.path.join(TEMP_DIR, filename)

            logger.info(f"Downloading paper {paper_id} from {pdf_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(filepath, "wb") as f:
                            f.write(content)
                        logger.info(f"Successfully downloaded: {paper_id}")
                        return filepath
                    logger.error(f"Failed to download {paper_id}: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error downloading {paper_id}: {str(e)}")
            return None

    async def download_papers(self, papers: List[dict]) -> Dict[str, str]:
        """Download all papers in parallel."""
        tasks = []
        for paper in papers:
            tasks.append(self.download_paper(paper))

        results = await asyncio.gather(*tasks)
        
        # Dictionary mapping paper IDs to file paths
        paper_paths = {}
        successful = 0
        
        for paper, file_path in zip(papers, results):
            paper_id = paper["paper"]["id"]
            if file_path:
                paper_paths[paper_id] = file_path
                successful += 1
                
        logger.info(f"Downloaded {successful}/{len(papers)} papers successfully")
        return paper_paths

    def parse_paper_data(self, paper_entry: dict) -> Paper:
        """Convert raw paper data to Paper model."""
        paper_data = paper_entry["paper"]
        return Paper(
            paper_id=paper_data["id"],
            title=paper_data["title"],
            authors=paper_data["authors"],
            summary=paper_data["summary"],
            published_at=paper_data["publishedAt"],
            pdf_url=PDF_BASE_URL.format(id=paper_data["id"]),
        )
