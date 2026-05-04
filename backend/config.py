from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Google Sheets
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE", str(BASE_DIR / "an-helper-2e2bcd71c709.json"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1mFlnUi2HNMFCxxTXAzBc2IMwn32v2qq6IhCCPi5eM1w")

# Sheet names
SHEET_DON = os.getenv("SHEET_DON", "DON")
SHEET_DON2 = os.getenv("SHEET_DON2", "Don2")

# Cache DB
CACHE_DB = DATA_DIR / "cache.db"

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Tracking APIs (optional)
GHN_TOKEN = os.getenv("GHN_TOKEN", "")
VTP_TOKEN = os.getenv("VTP_TOKEN", "")

# Shipping rates
DON_RATE_PER_KG = 14000
DON_RATE_PER_M3 = 2100000
DON2_RATE_PER_KG = 28000

# Credentials directory for user-uploaded JSON files
CREDENTIALS_DIR = BASE_DIR / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)
