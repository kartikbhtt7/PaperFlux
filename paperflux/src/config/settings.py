import os

MONGODB_URI = "mongodb://localhost:27017/"
DB_NAME = "papers_summary_database"
COLLECTION_NAME = "papers"
HF_API_URL = "https://huggingface.co/api/daily_papers"
PDF_BASE_URL = "https://arxiv.org/pdf/{id}.pdf"
TEMP_DIR = "temp_papers"
