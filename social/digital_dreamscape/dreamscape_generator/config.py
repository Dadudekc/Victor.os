import os

# --- OpenAI Configuration ---
# API Key - Recommended to set via environment variable OPENAI_API_KEY
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]  # Fail if not set
# Model Selection - Default model to use for episode generation
# Can be overridden, e.g., via CLI. Use valid OpenAI API model IDs.
OPENAI_MODEL = "gpt-4o" # Example: gpt-4o, gpt-4-turbo, gpt-4o-mini, etc.
GENERATION_TEMPERATURE = 0.7
GENERATION_MAX_TOKENS = 2000 # Adjust as needed for episode length

# --- Ollama Configuration (Optional - If adding local LLM support later) ---
# OLLAMA_MODEL = "mistral"
# OLLAMA_TIMEOUT = 120

# --- Project Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates") # Restore template path
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
HISTORY_DIR = os.path.join(BASE_DIR, "history") # Add directory for chat history
MEMORY_DIR = os.path.join(OUTPUT_DIR, "memory") # Subdir in output for memory state
EPISODE_DIR = os.path.join(OUTPUT_DIR, "episodes") # Subdir in output for generated episodes
ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "archive") # Subdir for general archiving if needed

# --- Generator Settings ---
MAX_WORKERS = 1 # Use 1 worker for now to simplify sequential generation/state updates
USERNAME = os.getenv("USERNAME", "Developer") # Default username for prompts

# --- Logging Configuration ---
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# --- Discord (Optional) ---
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", None)

# --- Ensure Core Directories Exist ---
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(EPISODE_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True) 
