"""Project paths and constants shared by all steps."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw_py"            # raw JSON from the Python scraper
PROCESSED_DIR = ROOT / "data" / "processed_py"
REPORTS_DIR = ROOT / "reports_py"
LOG_DIR = ROOT / "logs"
SOURCES_FILE = ROOT / "config" / "report2_sources.json"
BRANDS_FILE = ROOT / "config" / "report2_brands.json"

# Vietnam uses UTC+7 all year (no daylight saving time), so a fixed offset is exact.
VN_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")

# Polite collection limits
PAGE_TIMEOUT_MS = 60_000        # max time to load one category page
DELAY_BETWEEN_PAGES_S = 5       # pause between two page requests
MAX_SCROLL_ROUNDS = 120         # infinite scroll: stop after this many rounds
STABLE_ROUNDS_TO_STOP = 4       # ... or when card count stops growing 4 times in a row
MAX_RETRIES = 1                 # retry a failed page once, then give up

# Validation limits (VND). Prices outside this range are treated as parse errors.
MIN_VALID_PRICE = 1_000
MAX_VALID_PRICE = 20_000_000


def now_vn() -> datetime:
    return datetime.now(VN_TZ)
