import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration Constants

# The root directory to monitor 
MONITOR_ROOT = r"F:\vibecode\sefs_root"

# Embedding Model
MODEL_NAME = "all-MiniLM-L6-v2"

# Clustering Parameters
# EPS: The maximum distance between two samples for one to be considered as in the neighborhood of the other.
# Higher EPS = Looser clusters (More files grouped together).
# Lower EPS = Stricter clusters (More separate clusters).
CLUSTER_EPS = 0.6  # Increased from 0.3 to allow better grouping of small files
CLUSTER_MIN_SAMPLES = 1 

METADATA_DIR = ".sefs_metadata"

# RAG Configuration
CHUNK_SIZE = 400  # words per chunk
CHUNK_OVERLAP = 50  # words overlap between chunks
TOP_K_CHUNKS = 5  # number of chunks to retrieve for RAG

# Gemini API Key (set via environment variable)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
