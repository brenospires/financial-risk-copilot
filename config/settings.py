import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "financial_risk_copilot.db"

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")
FRED_API_KEY = os.getenv("FRED_API_KEY")