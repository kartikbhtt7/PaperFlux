import streamlit as st
import asyncio
import threading
import os
import base64
from datetime import datetime
import time
import logging
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("paperflux.app")

from src.services.database import DatabaseService
from src.services.paper_processor import PaperProcessor
from src.services.scheduler import PaperScheduler
from src.config.settings import TEMP_DIR

os.makedirs(TEMP_DIR, exist_ok=True)

# Initialize services
db_service = DatabaseService()
paper_processor = PaperProcessor()

# Start the scheduler in the background
scheduler = PaperScheduler()

# Function to run asyncio tasks from Streamlit
def run_async(func):
    loop = asyncio.new_event_loop()
    return loop.run_until_complete(func)

# Function to trigger paper processing in background
def process_papers_background():
    try:
        st.session_state.processing_started = True
        run_async(paper_processor.process_papers())
        st.session_state.processing_started = False
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")
        st.session_state.processing_started = False

# Get download link for paper
def get_pdf_download_link(paper_id, paper_title):
    """Generate a direct download link for a paper PDF"""
    try:
        # Get the paper from the database
        paper = db_service.get_paper_by_id(paper_id)
        
        # Use the PDF URL stored in the database
        pdf_url = paper["pdf_url"]
        
        # Create direct link to the PDF
        href = f'<a href="{pdf_url}" target="_blank">Download PDF</a>'
        return href
    except Exception as e:
        logger.error(f"Error creating download link: {str(e)}")
        return "PDF download unavailable"

st.set_page_config(
    page_title="PaperFlux - AI Research Paper Insights",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processing_started' not in st.session_state:
    st.session_state.processing_started = False
if 'current_paper_index' not in st.session_state:
    st.session_state.current_paper_index = 0
if 'scheduler_started' not in st.session_state:
    st.session_state.scheduler_started = False
    # Start the scheduler when the app loads
    scheduler.start_scheduler()
    st.session_state.scheduler_started = True

# App header
st.title("📚 PaperFlux")
st.markdown("### AI Research Paper Insights")

# Sidebar
st.sidebar.header("About PaperFlux")
st.sidebar.markdown(
    """
    PaperFlux extracts and analyzes top AI research papers from Hugging Face's 
    daily curated list. Each paper is summarized and explained in depth.
    
    Papers are updated automatically once daily at 8:00 AM UTC on weekdays.
    """
)

# Display processing status
metadata = db_service.get_processing_metadata()
last_processed = metadata.last_processed_date.strftime("%Y-%m-%d %H:%M UTC")
next_processing = "8:00 AM UTC Tomorrow" if datetime.now(pytz.UTC).hour >= 8 else "8:00 AM UTC Today"

st.sidebar.markdown(f"**Last updated:** {last_processed}")
st.sidebar.markdown(f"**Next scheduled update:** {next_processing}")

# Processing controls
st.sidebar.header("Data Processing")
is_processing = metadata.is_processing or st.session_state.processing_started

if is_processing:
    st.sidebar.info("Processing papers... This may take several minutes.")
    st.sidebar.progress(0.5)  # Indeterminate progress bar
else:
    # Check if manual processing is allowed
    should_process = db_service.should_process_today()
    if should_process:
        if st.sidebar.button("Process Papers Now", key="process_btn"):
            # Start processing in background thread
            threading.Thread(target=process_papers_background).start()
            st.sidebar.info("Processing started! This may take several minutes.")
            time.sleep(1)  # Give time for the thread to start
            st.rerun()  # Rerun to update UI
    else:
        st.sidebar.success("Today's papers have already been processed! ✅")
        st.sidebar.info("Papers are automatically updated each weekday at 8:00 AM UTC.")

# Main content
tab1, tab2 = st.tabs(["📋 Paper List", "ℹ️ About"])

with tab1:
    # Get papers from database with caching
    papers = db_service.get_all_papers()
    
    if not papers:
        if is_processing:
            st.info("Loading papers... Please wait.")
        else:
            st.warning("No papers available yet. The system will automatically fetch the latest research papers at 8:00 AM UTC.")
    else:
        st.success(f"Displaying {len(papers)} research papers")
        
        # Use all papers without filtering
        filtered_papers = papers
            
        # Paper navigation
        st.sidebar.header("Paper Navigation")
        
        # Paper selection dropdown
        paper_titles = [f"{i+1}. {p['title'][:50]}..." for i, p in enumerate(filtered_papers)]
        selected_index = st.sidebar.selectbox(
            "Select Paper:", 
            range(len(paper_titles)),
            format_func=lambda i: paper_titles[i],
            index=st.session_state.current_paper_index
        )
        
        # Update current index if changed through dropdown
        if selected_index != st.session_state.current_paper_index:
            st.session_state.current_paper_index = selected_index
        
        # Previous/Next buttons
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("← Previous", disabled=st.session_state.current_paper_index <= 0):
                st.session_state.current_paper_index -= 1
                st.rerun()
        with col2:
            if st.button("Next →", disabled=st.session_state.current_paper_index >= len(filtered_papers) - 1):
                st.session_state.current_paper_index += 1
                st.rerun()
        
        # Display current paper position
        st.sidebar.markdown(f"**Paper {st.session_state.current_paper_index + 1} of {len(filtered_papers)}**")
        
        # Display the selected paper
        if filtered_papers:
            current_index = st.session_state.current_paper_index
            if current_index < len(filtered_papers):
                paper = filtered_papers[current_index]
                
                paper_id = paper["paper_id"]
                title = paper["title"]
                published_date = datetime.fromisoformat(paper["published_at"].replace('Z', '+00:00')).strftime("%b %d, %Y")
                
                # Format authors (limit to 3 with "et al." if more)
                authors_list = paper["authors"]
                if len(authors_list) > 3:
                    authors_text = ", ".join(author.get("name", "") for author in authors_list[:3]) + " et al."
                else:
                    authors_text = ", ".join(author.get("name", "") for author in authors_list)
                
                # Paper header
                st.markdown(f"## {title}")
                st.markdown(f"**Authors:** {authors_text}")
                st.markdown(f"**Published:** {published_date} | **Paper ID:** {paper_id}")
                
                # Paper download link
                pdf_link = get_pdf_download_link(paper_id, title)
                st.markdown(pdf_link, unsafe_allow_html=True)
                
                # Paper content in tabs
                paper_tab1, paper_tab2 = st.tabs(["Summary", "Detailed Analysis"])
                
                with paper_tab1:
                    st.markdown(paper["summary"])
                
                with paper_tab2:
                    if paper.get("explanation"):
                        st.markdown(paper["explanation"])
                    else:
                        st.warning("Detailed analysis not available for this paper.")

with tab2:
    st.markdown("""
    ## About PaperFlux
    
    PaperFlux is a tool designed to help researchers and AI enthusiasts stay up-to-date with the latest research in the field. 
    
    ### How it works
    
    1. **Data Collection**: We automatically fetch the daily curated papers from Hugging Face's API.
    2. **Automatic Processing**: Papers are processed every weekday at 8:00 AM UTC.
    3. **Document Analysis**: Each paper is downloaded and analyzed using Google's Gemini Pro AI.
    4. **API Load Balancing**: We automatically rotate between multiple API keys to prevent rate limiting issues.
    5. **Data Storage**: All information is cached in a MongoDB database for fast access.
    
    ### Features
    
    - **Daily Updates**: New papers are processed once per day automatically.
    - **In-depth Analysis**: Get detailed explanations of complex research.
    - **Original Access**: Download the original PDF of any paper.
    
    ### Technologies Used
    
    - Streamlit for the web interface
    - MongoDB for data storage
    - Google's Gemini Pro AI for paper analysis
    - Hugging Face API for paper collection
    """)

# Footer
st.markdown("---")
st.markdown("PaperFlux © 2025 | Built with Streamlit and Gemini Pro")
