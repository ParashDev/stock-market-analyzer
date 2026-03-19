# Stock Market Analyzer

Data-driven daily stock screening tool that analyzes all S&P 500 stocks, scores them across 5 weighted factors, and ranks the top 50 upside candidates with human-readable explanations. Automated pipeline runs every weekday morning via GitHub Actions and deploys an interactive dashboard to GitHub Pages.

**Live Dashboard:** [parashdev.github.io/stock-market-analyzer](https://parashdev.github.io/stock-market-analyzer/)

## Features

- **Top 50 Upside Stocks** — Scored by analyst targets, technical signals, momentum, volume, and news sentiment
- **8 Technical Scanners** — RSI oversold, MACD bullish crossover, golden cross, volume spike, Bollinger oversold, near 52-week low, top gainers/losers
- **Backtesting** — Simulates past picks and compares returns vs S&P 500 benchmark
- **Earnings Impact Analysis** — Measures average stock moves on earnings beats vs misses
- **Risk Metrics** — Volatility, Sharpe ratio, max drawdown for each stock
- **Sector-Relative Scoring** — Ranks stocks within their own sector, not just overall
- **Historical Accuracy Tracking** — Saves daily picks and tracks win rate over time
- **News & Catalysts** — Market headlines and company-specific news from Finnhub
- **Earnings Calendar** — Upcoming S&P 500 earnings with EPS estimates
- **Macro Context** — VIX, Treasury yields, Fed funds rate from FRED
- **Custom Watchlist** — Star stocks + add custom tickers via `watchlist.txt`
- **Mobile-Friendly** — Card-based layout with slide-out drawer navigation on mobile
- **Educational** — Every metric, indicator, and analysis explained in plain English for beginners

## Data Sources

| Source | API Key? | What It Provides | Fallback |
|--------|----------|------------------|----------|
| **yfinance** | No | Daily OHLCV, fundamentals, analyst targets, P/E, market cap | Primary source |
| **Finnhub** | Yes (free) | Market news, company news, sentiment, earnings calendar | Graceful skip |
| **FRED** | Yes (free) | VIX, 10Y/2Y Treasury yields, Fed funds rate | Graceful skip |
| **Wikipedia** | No | S&P 500 constituent list with sectors | Hardcoded fallback |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys (optional — core pipeline works without them)
cp .env.example .env
# Edit .env with your Finnhub and FRED API keys

# Run the pipeline
python scripts/01_clean.py          # Fetch prices + fundamentals (~3 min)
python scripts/02_fetch_news.py     # Fetch news + earnings (~2 min)
python scripts/03_transform.py      # Analyze + score + rank (~10 sec)

# View dashboard (open index.html directly, or serve it)
python -m http.server 8000
# Open http://localhost:8000
```

## Pipeline Architecture

```
Wikipedia ─────────┐
(S&P 500 tickers)  │
                   ├─→ 01_clean.py ──→ daily_prices.csv (126K rows)
yfinance ──────────┤                   fundamentals.csv (502 rows)
(prices, targets)  │                   macro.csv (38 rows)
                   │
FRED ──────────────┘
(VIX, yields)

Finnhub ───────────→ 02_fetch_news.py ──→ market_news.csv (100 articles)
(news, earnings)                          company_news.csv (222 articles)
                                          earnings_calendar.csv (392 events)
                                          past_earnings.csv (898 results)

All CSVs ──────────→ 03_transform.py ──→ dashboard_data.json (149 KB)
                     - RSI, MACD, Bollinger, MAs     dashboard_data.js
                     - 5-factor composite scoring     picks_history.json
                     - Backtesting (20-day lookback)
                     - Sector-relative rankings
                     - Earnings impact analysis
                     - Risk metrics (Sharpe, drawdown)
                     - Historical accuracy tracking
```

## Scoring Model

Each stock gets a composite score from 0–100 based on 5 weighted factors:

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| Analyst Upside | 30% | % below Wall Street consensus price target |
| Technical | 25% | RSI, MACD crossovers, MA positioning, Bollinger Bands |
| Momentum | 20% | 5-day (60%) and 20-day (40%) price momentum |
| News Sentiment | 15% | Keyword-based sentiment from recent headlines |
| Volume Signal | 10% | Volume relative to 20-day average |

When news data is unavailable, weights automatically redistribute to the other 4 factors.

## Analysis Features

### Backtesting
Looks back 20 trading days, re-runs the scoring model on historical data, picks the top 10, and measures their actual return vs the S&P 500 average.

### Earnings Impact
Analyzes past 90 days of S&P 500 earnings reports. Calculates average stock move for beats vs misses, beat rate, and shows recent events.

### Risk Metrics
For each stock: annualized volatility, Sharpe ratio (return per unit of risk), and maximum drawdown (worst peak-to-trough drop over the past year).

### Historical Accuracy
Saves each run's top 10 picks with prices. On subsequent runs, checks if those picks went up (win) or down (loss). Tracks win rate over time to validate the model.

### Sector-Relative Scoring
Ranks each stock within its own sector. A utility stock with P/E 18 is expensive for utilities but cheap vs tech — sector-relative scoring captures this.

## Data Quality & Cleaning

Documented cleaning decisions in `docs/cleaning-log.md`:

- Ticker normalization (BRK.B → BRK-B for yfinance compatibility)
- Wikipedia 403 fix (User-Agent header + fallback list with metadata)
- Minimum 100 trading days filter for MA calculations
- NaN/Inf sanitization for JSON serialization
- Dynamic score weight rebalancing when data sources are unavailable
- Earnings calendar filtered to S&P 500 stocks only

## API Keys Setup

1. **Finnhub** — Sign up at [finnhub.io](https://finnhub.io) → Dashboard → Copy API key (free, instant)
2. **FRED** — Request at [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) (free, instant)

**Local:** Add to `.env` file
```
FINNHUB_API_KEY=your_key_here
FRED_API_KEY=your_key_here
```

**GitHub Actions:** Add as repository secrets in Settings → Secrets → Actions

## Automation

GitHub Actions runs the full pipeline every weekday at **6 AM CST** (before market open):

1. Installs Python 3.11 + dependencies
2. Runs `01_clean.py` (fetch prices + fundamentals + macro)
3. Runs `02_fetch_news.py` (fetch news + earnings)
4. Runs `03_transform.py` (analyze + score + rank)
5. Deploys dashboard to GitHub Pages

## Custom Watchlist

Add tickers outside S&P 500 to `watchlist.txt`:
```
# Uncomment to add custom tickers
PLTR
SOFI
COIN
```

The pipeline will fetch data for these alongside S&P 500 stocks.

## Tech Stack

- **Python 3.11** — pandas, numpy, yfinance, ta (technical analysis), requests
- **Single-file HTML** — Tailwind CSS, Chart.js, vanilla JavaScript
- **GitHub Actions** — Scheduled cron, GitHub Pages deployment
- **No database** — CSV → JSON → static HTML (zero infrastructure)

## Why This Architecture

- **No Airflow/Prefect** — 3 scripts with clear dependencies don't need orchestration
- **No PostgreSQL** — <150K total rows; JSON is the "database"
- **No React/Next.js** — Single page, no routing, zero build step
- **No scikit-learn** — Transparent weighted formulas, not black-box ML
- **No paid APIs** — Everything runs on free tiers
