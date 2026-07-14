import os
from pathlib import Path

from dotenv import load_dotenv

# apps/api/src/carecall_api/config.py -> repo root is 4 levels up
REPO_ROOT = Path(__file__).resolve().parents[4]

load_dotenv(REPO_ROOT / '.env')

DATA_DIR = REPO_ROOT / 'data'
TRANSCRIPTS_PATH = DATA_DIR / 'raw' / 'carecall_transcripts.json'
QUESTIONS_PATH = DATA_DIR / 'evaluation' / 'carecall_questions.json'


def _env(new_name: str, legacy_name: str, default: str) -> str:
    """Prefer the CARECALL_-prefixed name; fall back to the pre-refactor
    unprefixed env var so existing .env files keep working."""
    return os.getenv(new_name, os.getenv(legacy_name, default))


# Operating modes
STORAGE_MODE = os.getenv('CARECALL_STORAGE_MODE', 'memory').lower()
RETRIEVAL_MODE = os.getenv('CARECALL_RETRIEVAL_MODE', 'hybrid').lower()
ANSWER_MODE = _env('CARECALL_ANSWER_MODE', 'ANSWER_MODE', 'mock').lower()
EXTRACTION_MODE = os.getenv('CARECALL_EXTRACTION_MODE', 'deterministic').lower()

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_CHAT_MODEL = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

# Retrieval tuning
LEXICAL_WEIGHT = float(os.getenv('CARECALL_LEXICAL_WEIGHT', '0.45'))
SEMANTIC_WEIGHT = float(os.getenv('CARECALL_SEMANTIC_WEIGHT', '0.55'))
TOP_K = int(os.getenv('CARECALL_TOP_K', '8'))
MIN_RELEVANCE_SCORE = float(os.getenv('CARECALL_MIN_RELEVANCE_SCORE', '0.15'))

# PostgreSQL (production-like mode only)
DATABASE_URL = os.getenv('DATABASE_URL', '')

BACKEND_PORT = int(os.getenv('BACKEND_PORT', '8000'))

# Observability
LOG_LEVEL = os.getenv('CARECALL_LOG_LEVEL', 'INFO').upper()

# Audit trail privacy: question text is hashed by default; a short,
# truncated preview is only ever persisted if this is explicitly enabled.
# See docs/security/roles-and-privacy.md.
AUDIT_RETAIN_QUESTION_PREVIEW = os.getenv('CARECALL_AUDIT_RETAIN_QUESTION_PREVIEW', 'false').lower() == 'true'

# Developer/admin-only surfaces (Why-this-answer audit drawer, Retrieval
# Lab) are hidden by default in production.
DEVELOPER_MODE = os.getenv('CARECALL_DEVELOPER_MODE', 'false').lower() == 'true'
