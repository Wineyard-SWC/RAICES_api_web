# Standard library imports
import os
# Third-party imports
from google import genai
# Local application imports



KEY = os.getenv("GEMINI_API_KEY")

def intializeGeminiClient() -> genai:
    GeminiClient = genai.Client(api_key=KEY)

    return GeminiClient
