# PaperFlux: AI Research Paper Insights

PaperFlux is a Streamlit based web application powered by Gemini that automatically fetches, analyzes, and explains the latest AI research papers from Hugging Face's daily curated list. Using Google's Gemini Pro AI, it provides in-depth explanations and technical breakdowns of complex research papers, making cutting-edge AI research more accessible.

## Features

- **Daily Updates**: Automatically fetches and processes new papers every weekday at ```8:00 AM UTC```
- **AI-Powered Analysis**: Uses Google's ```Gemini Pro``` to provide detailed explanations of complex research
- **Paper Library**: Browse through all processed papers with easy navigation
- **Technical Breakdowns**: Get in-depth explanations of mathematical concepts and methodologies
- **Critical Assessment**: Read AI-generated critical analysis of each paper
- **Responsive Interface**: User-friendly interface built with Streamlit

## System Architecture

PaperFlux follows a robust architecture for fetching, processing, and displaying research papers:

```mermaid
   flowchart TD
      A[Scheduler] -->|Daily trigger| B[Paper Processor]
      B -->|Fetch papers| C[Hugging Face API]
      B -->|Download PDFs| D[arXiv]
      B -->|Analyze content| E[Gemini Pro API]
      B -->|Store data| F[(MongoDB)]
      G[Streamlit UI] -->|Display papers| F
      H[User] -->|View papers| G

```

## System Flow

1. **Scheduled Polling**: Every weekday at 8:00 AM UTC, the scheduler checks if papers need to be processed
2. **Data Collection**: The application fetches the latest papers from Hugging Face's API
3. **PDF Processing**: Papers are downloaded from arXiv and stored temporarily
4. **AI Analysis**: Each paper is analyzed using Google's Gemini Pro API
5. **Data Storage**: Results are stored in MongoDB for quick access
6. **User Interface**: Users can browse all processed papers through the Streamlit interface

## Installation

### Prerequisites

- Python 3.8 or higher
- MongoDB database
- Google Gemini Pro API key(s)
- Poetry (dependency management)

### Local Setup with Poetry

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/paperflux.git
   cd paperflux
   ```

2. Install dependencies using Poetry:
   ```bash
   # Install Poetry if you haven't already
   # curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies
   poetry install
   ```

3. Create a `.env` file with your credentials (copy from `.env.example`):
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. Configure your environment variables:
   ```
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/paperflux
   GEMINI_API_KEY1=your_gemini_api_key_1
   GEMINI_API_KEY2=your_gemini_api_key_2
   # Add more API keys as needed for load balancing
   ```

5. Run the Streamlit app with Poetry:
   ```bash
   poetry run streamlit run app.py
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
