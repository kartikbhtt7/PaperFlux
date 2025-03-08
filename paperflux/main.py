import logging
from src.scheduler.jobs import PaperProcessingScheduler
from src.web.app import PaperFluxUI
import streamlit as st

# logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paperflux.main")
logger.info("Initializing PaperFlux")

# Initialize scheduler
logger.info("Creating scheduler")
scheduler = PaperProcessingScheduler()

# Start scheduler
logger.info("Starting scheduler")
scheduler.start()
logger.info("Scheduler started")

# Create and render UI
logger.info("Creating UI")
ui = PaperFluxUI(scheduler=scheduler)
logger.info("Rendering UI")
ui.render_app()
