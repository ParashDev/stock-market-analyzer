# Stock Market Analyzer

Data-driven daily stock screening tool that analyzes all S&P 500 stocks, scores them across 5 weighted factors, and ranks the top 50 upside candidates with human-readable explanations. Automated pipeline runs every weekday at 6 AM CST via GitHub Actions and deploys an interactive dashboard to GitHub Pages.

**Live Dashboard:** [parashdev.github.io/stock-market-analyzer](https://parashdev.github.io/stock-market-analyzer/)

## Features

- **Stocks to Watch for Tomorrow** — Top 50 scored by analyst targets, technical signals, momentum, volume, and news sentiment with top 10 highlighted as strongest conviction picks
- **Previous Day Catalyst Timeline** — Hour-by-hour SPY intraday breakdown matched with news events showing what triggered market moves, with clickable links to source articles
- **8 Technical Scanners** — RSI oversold, MACD bullish crossover, golden cross, volume spike, Bollinger oversold, near 52-week low, top gainers/losers — each with detailed educational explanation
- **Backtesting** — Simulates past picks (20-day lookback) and compares returns vs S&P 500 benchmark with known-limitation disclosure
- **Earnings Impact Analysis** — Measures average stock moves on earnings beats vs misses across 90 days of S&P 500 reports
- **Risk Metrics** — Volatility, Sharpe ratio, max drawdown for each stock with plain-English risk profile
- **Sector-Relative Scoring** — Ranks stocks within their own sector with sector P/E comparison
- **Historical Accuracy Tracking** — Saves daily top 10 picks, evaluates performance over time, tracks win rate
- **News & Catalysts** — Market headlines and company-specific news from Finnhub with clickable source links
- **Earnings Calendar** — Upcoming S&P 500 earnings with company names and EPS estimates
- **Macro Context** — VIX, Treasury yields, Fed funds rate from FRED
- **Custom Watchlist** — Star stocks in the dashboard (localStorage) + add custom tickers via `watchlist.txt`
- **Mobile-Friendly** — Card-based stock layout, slide-out drawer navigation, touch-optimized expand panels
- **Educational Dashboard** — Every metric, indicator, scanner, and analysis section explained in plain English for beginners with a full glossary

## Data Sources

| Source | API Key? | What It Provides | Fallback |
|--------|----------|------------------|----------|
| **yfinance** | No | Daily OHLCV, hourly SPY intraday, fundamentals, analyst targets, P/E, market cap | Primary source |
| **Finnhub** | Yes (free) | Market news, company news, sentiment, earnings calendar, past earnings results | Graceful skip |
| **FRED** | Yes (free) | VIX, 10Y/2Y Treasury yields, Fed funds rate | Graceful skip |
| **Wikipedia** | No | S&P 500 constituent list with GICS sectors | Hardcoded fallback with 100 stocks + metadata |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys (optional — core pipeline works without them)
cp .env.example .env
# Edit .env with your Finnhub and FRED API keys

# Run the pipeline
python scripts/01_clean.py          # Fetch prices + fundamentals + SPY hourly (~3 min)
python scripts/02_fetch_news.py     # Fetch news + earnings + past earnings (~2 min)
python scripts/03_transform.py      # Analyze + score + rank + backtest (~15 sec)

# View dashboard — just open index.html directly in your browser
# Or serve it:
python -m http.server 8000
```

## Pipeline Architecture

```
Wikipedia ─────────┐
(S&P 500 tickers)  │
                   ├─→ 01_clean.py ──→ daily_prices.csv (126K rows)
yfinance ──────────┤                   fundamentals.csv (502 rows)
(prices, targets,  │                   macro.csv (38 rows)
 SPY hourly)       │                   spy_hourly.csv (35 bars)
                   │
FRED ──────────────┘
(VIX, yields)

Finnhub ───────────→ 02_fetch_news.py ──→ market_news.csv (100 articles)
(news, earnings)                          company_news.csv (222 articles)
                                          earnings_calendar.csv (392 events)
                                          past_earnings.csv (898 results)

All CSVs ──────────→ 03_transform.py ──→ dashboard_data.json (165 KB)
                     - RSI, MACD, Bollinger, MAs     dashboard_data.js
                     - 5-factor composite scoring     picks_history.json
                     - Backtesting (20-day lookback)
                     - Sector-relative rankings
                     - Earnings impact analysis
                     - Risk metrics (Sharpe, drawdown)
                     - Catalyst timeline (SPY + news)
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

### Previous Day Catalyst Timeline
Fetches hourly SPY (S&P 500 ETF) data and matches each hour with timestamped news headlines from Finnhub. Shows an intraday price chart, identifies significant moves (>0.3%), and auto-generates a narrative explaining what drove the market. News headlines are clickable links to the source articles.

### Backtesting
Looks back 20 trading days, re-runs the full scoring model on historical data, picks the top 10, and measures their actual return vs the S&P 500 average. Includes a known-limitation note about lookahead bias from using current analyst targets.

### Earnings Impact
Analyzes past 90 days of S&P 500 earnings reports. Calculates average stock move on earnings day for beats vs misses, beat rate, and shows a table of recent events with EPS surprise and price reaction.

### Risk Metrics
For each stock: annualized volatility, Sharpe ratio (return per unit of risk), and maximum drawdown (worst peak-to-trough drop over the past year). Color-coded with plain-English risk assessment in the expand panel.

### Historical Accuracy
Saves each run's top 10 picks with prices to `picks_history.json`. On subsequent runs, checks if those picks went up (win) or down (loss) after 5+ trading days. Tracks win rate over time to validate the model.

### Sector-Relative Scoring
Ranks each stock within its own sector. Shows sector rank, sector count, and sector median P/E in the expand panel. A utility stock with P/E 18 is expensive for utilities but cheap vs tech — this scoring captures that.

## Data Quality & Cleaning

Documented cleaning decisions in `docs/cleaning-log.md`:

- Ticker normalization (BRK.B → BRK-B for yfinance compatibility)
- Wikipedia 403 fix (User-Agent header + hardcoded fallback with sector metadata)
- Minimum 100 trading days filter for MA calculations
- NaN/Inf sanitization for JSON serialization
- Dynamic score weight rebalancing when data sources are unavailable
- Earnings calendar filtered to S&P 500 stocks only
- All timestamps converted to CST (America/Chicago)

## API Keys Setup

1. **Finnhub** — Sign up at [finnhub.io](https://finnhub.io) → Dashboard → Copy API key (free, instant)
2. **FRED** — Request at [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) (free, instant)

**Local:** Add to `.env` file (git-ignored, never committed)
```
FINNHUB_API_KEY=your_key_here
FRED_API_KEY=your_key_here
```

**GitHub Actions:** Add as repository secrets in Settings → Secrets and variables → Actions

## Automation

GitHub Actions runs the full pipeline every weekday at **6 AM CST** (before market open):

1. Installs Python 3.11 + dependencies
2. Runs `01_clean.py` (fetch prices + fundamentals + macro + SPY hourly)
3. Runs `02_fetch_news.py` (fetch news + earnings + past earnings)
4. Runs `03_transform.py` (analyze + score + rank + backtest + catalyst timeline)
5. Deploys dashboard to GitHub Pages

Also triggers on push to `main` when scripts, `index.html`, or `requirements.txt` change.

Total runtime: ~6-7 minutes per run. Public repos get unlimited GitHub Actions minutes.

## Custom Watchlist

Add tickers outside S&P 500 to `watchlist.txt`:
```
# Uncomment to add custom tickers
PLTR
SOFI
COIN
```

The pipeline fetches data for these alongside S&P 500 stocks. You can also star any stock in the dashboard to save it to your browser's watchlist (localStorage).

## Dashboard Sections

| Section | What It Shows |
|---------|---------------|
| **Pipeline & Methodology** | Data sources, cleaning decisions, ETL process, scoring weights |
| **Market Pulse** | Avg change, advancers/decliners, breadth, VIX, Treasury yields |
| **Sector Map** | 11 GICS sectors with daily performance + bar chart |
| **What Happened Yesterday** | Hourly SPY timeline with news catalysts and intraday chart |
| **Stocks to Watch** | Top 50 ranked stocks with expandable analysis cards |
| **Risk Profile** | Avg volatility, Sharpe ratio, max drawdown of top 50 |
| **Technical Scanners** | 8 pattern scanners with educational descriptions |
| **News & Catalysts** | Market + company headlines with clickable links |
| **Earnings Calendar** | Upcoming S&P 500 earnings with company names |
| **Backtest** | 20-day historical pick performance vs benchmark |
| **Earnings Impact** | Beat rate, avg moves on beats/misses |
| **Accuracy Tracker** | Win rate and avg return of past picks over time |
| **Learn the Terms** | Glossary of RSI, MACD, Bollinger, Golden Cross, P/E, etc. |

## Tech Stack

- **Python 3.11** — pandas, numpy, yfinance, ta (technical analysis), requests
- **Single-file HTML** — Tailwind CSS, Chart.js, vanilla JavaScript
- **GitHub Actions** — Scheduled cron (6 AM CST weekdays), GitHub Pages deployment
- **No database** — CSV → JSON → static HTML (zero infrastructure)

## Why This Architecture

- **No Airflow/Prefect** — 3 scripts with clear dependencies don't need orchestration
- **No PostgreSQL** — <150K total rows; JSON is the "database"
- **No React/Next.js** — Single page, no routing, zero build step
- **No scikit-learn** — Transparent weighted formulas, not black-box ML
- **No paid APIs** — Everything runs on free tiers forever
