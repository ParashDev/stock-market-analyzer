"""Stock Market Analyzer - Configuration
Single source of truth for all pipeline settings."""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
DASHBOARD_JSON = DATA_DIR / "dashboard_data.json"

for _d in [RAW_DIR, CLEANED_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── API Keys ───────────────────────────────────────────────────────────
# Load from .env file if present (local dev convenience)
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")
FRED_API_KEY = os.environ.get("FRED_API_KEY")

# ── Technical Indicator Parameters ─────────────────────────────────────
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

MA_SHORT = 50
MA_LONG = 200

BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

VOLUME_AVG_PERIOD = 20
VOLUME_SPIKE_THRESHOLD = 2.0

# ── Scoring Weights ────────────────────────────────────────────────────
WEIGHTS = {
    "analyst_upside": 0.30,
    "technical":      0.25,
    "momentum":       0.20,
    "volume_signal":  0.10,
    "news_sentiment": 0.15,
}

WEIGHTS_NO_NEWS = {
    "analyst_upside": 0.35,
    "technical":      0.30,
    "momentum":       0.20,
    "volume_signal":  0.15,
}

# ── Pipeline Settings ──────────────────────────────────────────────────
PRICE_HISTORY_DAYS = 365
TOP_N = 50
NEWS_TOP_MOVERS = 50
MIN_TRADING_DAYS = 100
BACKTEST_LOOKBACK_DAYS = 20
PICKS_HISTORY_FILE = DATA_DIR / "picks_history.json"

# ── Data Source URLs ───────────────────────────────────────────────────
SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
FINNHUB_BASE = "https://finnhub.io/api/v1"
FRED_BASE = "https://api.stlouisfed.org/fred"

FRED_SERIES = {
    "vix":          "VIXCLS",
    "treasury_10y": "DGS10",
    "treasury_2y":  "DGS2",
    "fed_funds":    "DFF",
}

# ── Sector Colors ──────────────────────────────────────────────────────
SECTOR_COLORS = {
    "Information Technology": "#3B82F6",
    "Health Care":            "#10B981",
    "Financials":             "#F59E0B",
    "Consumer Discretionary": "#EF4444",
    "Communication Services": "#8B5CF6",
    "Industrials":            "#6B7280",
    "Consumer Staples":       "#14B8A6",
    "Energy":                 "#F97316",
    "Utilities":              "#06B6D4",
    "Real Estate":            "#EC4899",
    "Materials":              "#84CC16",
}

# ── Sentiment Keywords ─────────────────────────────────────────────────
POSITIVE_WORDS = {
    "upgrade", "beat", "beats", "surpass", "record", "growth", "bullish",
    "outperform", "buy", "strong", "positive", "surge", "rally", "gain",
    "profit", "revenue", "raise", "boost", "innovate", "breakthrough",
    "approval", "partnership", "expand", "dividend", "buyback", "exceeds",
}

NEGATIVE_WORDS = {
    "downgrade", "miss", "misses", "decline", "bearish", "sell", "weak",
    "underperform", "loss", "lawsuit", "investigation", "recall", "cut",
    "warning", "debt", "layoff", "bankruptcy", "fraud", "probe", "fine",
    "delay", "concern", "risk", "drop", "crash", "slump", "downturn",
}
