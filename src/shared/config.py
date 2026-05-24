import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = "llama-3.3-70b-versatile"
WHISPER_MODEL = "tiny"
ASSETS_DIR = Path("src/library/assets")
FPS = 24
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
CHUNK_DURATION = 30.0
SIMILARITY_THRESHOLD = 0.6
ONLINE_SVG_FALLBACK = True