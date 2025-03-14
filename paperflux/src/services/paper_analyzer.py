import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv
import os
import time
import logging

load_dotenv()

logger = logging.getLogger("paperflux.paper_analyzer")

class PaperAnalyzer:
    def __init__(self):
        logger.info("Initializing PaperAnalyzer")
        load_dotenv()

        self.api_keys = [
            value
            for key, value in os.environ.items()
            if key.startswith("GEMINI_API_KEY")
        ]
        
        if not self.api_keys:
            logger.error("No Gemini API keys found in environment variables")
            raise ValueError("No Gemini API keys found. Please add GEMINI_API_KEY* to .env file")
            
        self.key_index = 0
        genai.configure(api_key=self.api_keys[0])
        self.model = genai.GenerativeModel("gemini-1.5-pro-latest")
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def change_api_key(self):
        """Rotate to the next API key"""
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        genai.configure(api_key=self.api_keys[self.key_index])
        logger.info(f"Switched to API key index: {self.key_index}")

    def analyze_paper(self, pdf_path: str) -> str:
        """Analyze a paper using Gemini API"""
        logger.info(f"Analyzing paper: {pdf_path}")
        
        try:
            uploaded_file = genai.upload_file(pdf_path)
            prompt = """Analyze this research paper thoroughly and provide:

            # Paper Title
            ## Core Contribution
            ## Technical Breakdown
            - Detailed mathematical concepts and intuition with in depth explanation
            - Include in depth explanation of each mathematical concept with proper reasoning
            - Explain each and every term used in the paper properly
            - Key algorithms and methodologies
            ## Critical Assessment
            ## Potential Applications
            
            Include detailed mathematical expressions and thorough explanations."""
            
            max_attempts = 3
            attempt = 0
            
            while attempt < max_attempts:
                attempt += 1
                try:
                    logger.info(f"Attempt {attempt} to analyze paper with api key {self.key_index}")
                    response = self.model.generate_content(
                        [prompt, uploaded_file],
                        safety_settings=self.safety_settings,
                        generation_config={"temperature": 0.2},
                    )
                    
                    # Success, rotate API key for load balancing
                    self.change_api_key()
                    
                    # Clean up
                    try:
                        genai.delete_file(uploaded_file.name)
                    except Exception as e:
                        logger.warning(f"Failed to delete uploaded file: {str(e)}")
                    
                    return response.text
                    
                except Exception as e:
                    logger.error(f"Error analyzing paper (attempt {attempt}): {str(e)}")
                    
                    # If rate limited, wait and try again with different key
                    if "429" in str(e):
                        wait_time = min(60 * attempt, 180)  # Progressive backoff
                        logger.info(f"Rate limited, waiting {wait_time} seconds")
                        time.sleep(wait_time)
                        self.change_api_key()
                    else:
                        raise
            
            raise Exception(f"Failed to analyze paper after {max_attempts} attempts")
                
        except Exception as e:
            logger.error(f"Failed to analyze paper: {str(e)}")
            return f"Error analyzing paper: {str(e)}"
