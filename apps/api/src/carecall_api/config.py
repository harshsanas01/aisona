import os
from pathlib import Path
from dotenv import load_dotenv

# apps/api/src/carecall_api/config.py -> repo root is 4 levels up
REPO_ROOT = Path(__file__).resolve().parents[4]

load_dotenv(REPO_ROOT / '.env')

DATA_DIR = REPO_ROOT / 'data'
TRANSCRIPTS_PATH = DATA_DIR / 'raw' / 'carecall_transcripts.json'
QUESTIONS_PATH = DATA_DIR / 'evaluation' / 'carecall_questions.json'

ANSWER_MODE = os.getenv('ANSWER_MODE', 'mock').lower()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_CHAT_MODEL = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
BACKEND_PORT = int(os.getenv('BACKEND_PORT', '8000'))
