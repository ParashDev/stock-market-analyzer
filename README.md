# Stock Market Analyzer

Daily S&P 500 upside screening powered by yfinance, Finnhub, and FRED. Runs every weekday at 8 PM ET via GitHub Actions, deploys to GitHub Pages.

## What It Does

- Fetches daily prices for all S&P 500 stocks
- Calculates technical indicators (RSI, MACD, Bollinger Bands, MA crossovers)
- Scores each stock on analyst upside, technicals, momentum, volume, and news sentiment
- Ranks top 50 stocks with human-readable reasons for each pick
- Runs 8 technical scanners (RSI oversold, golden cross, volume spike, etc.)
- Pulls market news, company news, and upcoming earnings calendar

## Data Sources

| Source | API Key? | What |
|--------|----------|------|
| yfinance | No | Prices, fundamentals, analyst targets |
| Finnhub | Yes (free) | Market/company news, sentiment, earnings calendar |
| FRED | Yes (free) | VIX, Treasury yields, Fed funds rate |

## Quick Start

```bash
pip install -r requirements.txt

# Set API keys (optional - pipeline works without them)
cp .env.example .env
# Edit .env with your keys

# Run pipeline
python scripts/01_clean.py
python scripts/02_fetch_news.py
python scripts/03_transform.py

# View dashboard
python -m http.server 8000
# Open http://localhost:8000
```

## Pipeline

```
yfinance ──┐
           ├─> 01_clean.py ──> daily_prices.csv + fundamentals.csv
FRED ──────┘                                           │
                                                       v
Finnhub ──────> 02_fetch_news.py ──> news CSVs ──> 03_transform.py ──> dashboard_data.json ──> index.html
```

## API Keys Setup

1. **Finnhub**: Sign up at [finnhub.io](https://finnhub.io) → Dashboard → Copy API key
2. **FRED**: Sign up at [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) → Request key

For GitHub Actions, add as repository secrets: `FINNHUB_API_KEY` and `FRED_API_KEY`

## Architecture

Same pattern as EPL-Analysis and nfl-fantasy-draft-analyzer:
- Numbered Python ETL scripts with config.py
- Graceful degradation (news/macro optional)
- Single-file HTML dashboard (Tailwind + Chart.js)
- GitHub Actions automation → GitHub Pages deployment
