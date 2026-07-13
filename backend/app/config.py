import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
TRANSCRIPTS_PATH = DATA_DIR / 'carecall_transcripts.json'
QUESTIONS_PATH = DATA_DIR / 'carecall_questions.json'

ANSWER_MODE = os.getenv('ANSWER_MODE', 'mock').lower()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_CHAT_MODEL = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
BACKEND_PORT = int(os.getenv('BACKEND_PORT', '8000'))
