import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "financial_risk_copilot.db"

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")
SEC_REQUEST_DELAY_SECONDS = float(
    os.getenv("SEC_REQUEST_DELAY_SECONDS", "0.2")
)
SEC_REQUEST_TIMEOUT_SECONDS = int(
    os.getenv("SEC_REQUEST_TIMEOUT_SECONDS", "30")
)

FRED_API_KEY = os.getenv("FRED_API_KEY")

LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-coder:7b")
OLLAMA_CONTEXT_WINDOW_TOKENS = int(
    os.getenv("OLLAMA_CONTEXT_WINDOW_TOKENS", "8192")
)

INVESTMENT_PROFILE = os.getenv(
    "INVESTMENT_PROFILE",
    "CONSERVATIVE",
).upper()
