import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ===========================
# Configuration
# ===========================

# Mode
LOCAL_MODE = os.environ.get("LOCAL_MODE", "false").lower() == "true"

# API Keys
API_KEY = os.environ.get("CHATBOT_API_KEY", "default-dev-key")
INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "SuperSecretInternalKey123")

# LLM Configuration
CLOUD_MODE = os.environ.get("CLOUD_MODE", "false").lower() == "true"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

# If Cloud Mode is on, we might use a different URL or Key if provided
if CLOUD_MODE:
    OLLAMA_HOST = os.environ.get("CLOUD_API_URL", OLLAMA_HOST)
    
CLOUD_API_KEY = os.environ.get("CLOUD_API_KEY", "")

# Default to a smaller model for local users if not specified, 
# but if cloud mode is true, we might want a bigger default or user specified.
LLM_MODEL = os.environ.get("LLM_MODEL", "llama3:8b") 

# Paths
DATA_DIR_RAW = "data/wiki_pages"
DATA_DIR_CLEANED = "data/wiki_pages_cleaned"
INDEX_PATH = "faiss_index"

# Wiki Fetching
WIKI_API_URL_DEFAULT = "https://minecraft.fandom.com/api.php"
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 8))

def get_llm_model_name():
    return LLM_MODEL

def is_local_mode():
    return LOCAL_MODE
