import streamlit as st
import asyncio
import threading
import time
import logging
from src.scheduler.jobs import PaperProcessingScheduler
from src.services.database import DatabaseService

logger = logging.getLogger("paperflux.app")


class PaperFluxUI:
    def __init__(self, scheduler: PaperProcessingScheduler):
        logger.info("Initializing PaperFluxUI")
        self.scheduler = scheduler
        self.db = DatabaseService()
        self.callback_registered = False

        # Register callback if not already done
        if not self.callback_registered:
            logger.info("Registering refresh callback")
            self.scheduler.register_refresh_callback(self.refresh_callback)
            self.callback_registered = True

        # Set up the page configuration
        logger.info("Setting up page config")
        st.set_page_config(
            page_title="PaperFlux - Research Paper Summaries",
            page_icon="📚",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # Add custom CSS
        st.markdown(
            """
        <style>
        .main {
            padding: 2rem;
        }
        .paper-title {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .author-list {
            margin-bottom: 1rem;
            color: #666;
        }
        .summary-header {
            font-size: 1.3rem;
            font-weight: bold;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        .explanation-header {
            font-size: 1.5rem;
            font-weight: bold;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .paper-date {
            color: #888;
            font-style: italic;
        }
        .paper-container {
            padding: 1.5rem;
            border-radius: 10px;
            background-color: #f8f9fa;
            margin-bottom: 2rem;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )
        logger.info("PaperFluxUI initialization complete")

    def refresh_callback(self):
        """Callback that will be called when a new paper is processed"""
        logger.info("Refresh callback triggered")
        # Use Streamlit's session state to signal a refresh is needed
        if "needs_rerun" not in st.session_state:
            st.session_state["needs_rerun"] = True

    def render_app(self):
        """Render the main app content"""
        # App header
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("📚 PaperFlux")
            st.subheader("Curated Research Papers with AI-Generated Summaries")
        with col2:
            if st.button("Refresh Data", key="refresh_button"):
                # Clear session state
                if "current_paper_index" in st.session_state:
                    del st.session_state["current_paper_index"]
                # Trigger rerun
                st.rerun()

        # Get papers from database
        papers = self.db.get_all_papers()

        # Show processing status if no papers
        if not papers:
            st.info(
                "⏳ Waiting for papers to be processed. Please wait or check back later."
            )

            # Add progress indicator
            if self.scheduler._running:
                st.markdown("### 🔄 Paper processing is currently running...")
                progress = st.progress(0)
                for i in range(100):
                    # Simulating progress as we don't know the actual progress
                    time.sleep(0.1)
                    progress.progress(i + 1)
                    # Break if papers are available or processing stopped
                    updated_papers = self.db.get_all_papers(max_cache_age_seconds=1)
                    if updated_papers or not self.scheduler._running:
                        if updated_papers:
                            st.success("✅ Papers have been processed!")
                            time.sleep(1)
                            st.rerun()
                        break
            else:
                st.warning(
                    "Paper processing is not currently running. It may be scheduled for midnight."
                )

            # Add manual trigger button
            if st.button("Process Papers Now", key="process_now"):
                st.info("Starting paper processing...")
                # Use threading to avoid blocking the Streamlit interface
                threading.Thread(
                    target=lambda: asyncio.run(self.scheduler.process_papers()),
                    daemon=True,
                ).start()
                st.rerun()

            return

        # Sidebar for navigation
        with st.sidebar:
            st.header("Navigation")

            # Store current paper index in session state
            if "current_paper_index" not in st.session_state:
                st.session_state["current_paper_index"] = 0

            # Paper selection widget
            paper_titles = [p["title"] for p in papers]
            selected_title = st.selectbox(
                "Select Paper",
                paper_titles,
                index=st.session_state["current_paper_index"],
            )

            # Update current paper index when selection changes
            st.session_state["current_paper_index"] = paper_titles.index(selected_title)

            # Navigation buttons
            col1, col2 = st.columns(2)
            with col1:
                prev_disabled = st.session_state["current_paper_index"] <= 0
                if st.button("Previous", disabled=prev_disabled):
                    st.session_state["current_paper_index"] -= 1
                    st.rerun()

            with col2:
                next_disabled = (
                    st.session_state["current_paper_index"] >= len(papers) - 1
                )
                if st.button("Next", disabled=next_disabled):
                    st.session_state["current_paper_index"] += 1
                    st.rerun()

            st.markdown(
                f"Paper {st.session_state['current_paper_index'] + 1} of {len(papers)}"
            )

            # Additional information
            st.subheader("Information")
            st.info(
                "Papers are automatically refreshed daily at midnight. "
                "The database is cleared and new papers are downloaded and processed."
            )

            # Show processing date
            st.caption("Last Updated:")
            if (
                papers
                and "processed_at" in papers[st.session_state["current_paper_index"]]
            ):
                processed_time = papers[st.session_state["current_paper_index"]][
                    "processed_at"
                ]
                st.caption(f"{processed_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Display selected paper
        if papers:
            current_paper = papers[st.session_state["current_paper_index"]]
            self.display_paper(current_paper)

    def display_paper(self, paper):
        """Display a single paper with all its details"""
        # Paper title
        st.markdown(
            f"<h1 class='paper-title'>{paper['title']}</h1>", unsafe_allow_html=True
        )

        # Publication date and authors
        col1, col2 = st.columns([1, 3])
        with col1:
            published_date = paper.get("published_at", "")
            if published_date:
                try:
                    if isinstance(published_date, str):
                        formatted_date = published_date.split("T")[0]
                    else:
                        formatted_date = published_date.strftime("%Y-%m-%d")
                    st.markdown(f"**Published:** {formatted_date}")
                except:
                    st.markdown(f"**Published:** {published_date}")

        with col2:
            # Format authors
            authors = paper.get("authors", [])
            if authors:
                if isinstance(authors[0], dict) and "name" in authors[0]:
                    author_names = [a.get("name", "") for a in authors]
                else:
                    author_names = [str(a) for a in authors]

                st.markdown(f"**Authors:** {', '.join(author_names)}")

        # PDF download button
        if paper.get("pdf_url"):
            st.markdown("### 📄 Paper Download")
            st.markdown(f"[Download Original PDF]({paper['pdf_url']})")

        # Paper summary
        st.markdown("<h2 class='summary-header'>Abstract</h2>", unsafe_allow_html=True)
        st.markdown(paper.get("summary", "No summary available."))

        # Paper explanation
        if paper.get("explanation"):
            st.markdown(
                "<h2 class='explanation-header'>AI Analysis</h2>",
                unsafe_allow_html=True,
            )

            with st.expander("Show Full Analysis", expanded=True):
                st.markdown(paper["explanation"])
        else:
            st.warning("Detailed analysis not available for this paper.")

        # Footer
        st.markdown("---")
        st.caption("PaperFlux - Powered by Gemini")
