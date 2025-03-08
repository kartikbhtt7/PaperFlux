import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv
import os, time


class PaperAnalyzer:
    def __init__(self):
        load_dotenv()

        self.api_keys = [
            value
            for key, value in os.environ.items()
            if key.startswith("GEMINI_API_KEY")
        ]
        assert len(self.api_keys) > 0
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
        self.key_index = (self.key_index + 1) % len(self.api_keys)
        genai.configure(api_key=self.api_keys[self.key_index])
        print(f"Switched API key: {self.api_keys[self.key_index]}")

    def analyze_paper(self, pdf_path: str) -> str:
        uploaded_file = genai.upload_file(pdf_path)
        prompt = """Analyze this research paper thoroughly and provide:

        # Paper Title
        ## Core Contribution
        ## Technical Breakdown
        - Detailed mathematical concepts and intuition with in depth explanation
        - Key algorithms and methodologies
        ## Visual Analysis
        ## Critical Assessment
        ## Potential Applications
        
        Include detailed mathematical expressions and thorough explanations."""
        while True:
            try:
                response = self.model.generate_content(
                    [prompt, uploaded_file],
                    safety_settings=self.safety_settings,
                    generation_config={"temperature": 0.2},
                )

                self.change_api_key()
                genai.delete_file(uploaded_file.name)
                return response.text
            except Exception as e:
                print(f"Unexpected error: {e}")
                if "429" not in str(e):
                    return
                time.sleep(2000)
                self.change_api_key()
