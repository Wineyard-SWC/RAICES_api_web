from dotenv import load_dotenv

# Standard library imports
import os
# Third-party imports
from google import genai
# Local application imports

load_dotenv(dotenv_path='../.env')

KEY = os.getenv("GEMINI_API_KEY")

def intializeGeminiClient() -> genai:
    GeminiClient = genai.Client(api_key=KEY)

    return GeminiClient
