# Pipeline Architecture

## Execution Order

```
01_clean.py  →  02_fetch_news.py  →  03_transform.py
  (required)       (optional)          (required)
```

02 depends on 01 (reads daily_prices.csv to identify top movers).
03 depends on 01 (required) and 02 (optional enrichment).

## Script Responsibilities

### 01_clean.py (~10 min)
- Fetches S&P 500 constituent list from Wikipedia
- Batch-downloads 1 year of daily OHLCV via yfinance
- Iterates through ~500 tickers for fundamentals via yfinance .info
- Fetches VIX, Treasury yields from FRED API

### 02_fetch_news.py (~2 min)
- Fetches general market news from Finnhub
- Identifies top 50 movers from price data
- Fetches company-specific news for those movers
- Scores sentiment with keyword matching
- Fetches 7-day earnings calendar

### 03_transform.py (~5 sec)
- Calculates RSI, MACD, Bollinger Bands, moving averages for all stocks
- Scores on 5 dimensions: analyst upside, technical, momentum, volume, news
- Ranks top 50 by composite score
- Generates human-readable reasons for each pick
- Runs 8 scanner patterns
- Outputs dashboard_data.json

## Graceful Degradation

| Missing | Impact |
|---------|--------|
| FRED_API_KEY | No VIX/yields in market pulse |
| FINNHUB_API_KEY | No news, no earnings calendar, scoring reweights |
| Wikipedia down | Falls back to hardcoded top 100 tickers |
| yfinance .info fails for a ticker | Wikipedia data used, no analyst target |

## Why Not...

- **Airflow/Prefect**: 3 scripts don't need orchestration
- **PostgreSQL**: <150K rows total, JSON is the "database"
- **React**: Single page, no routing, zero build step
- **scikit-learn**: Weighted scoring formula, not ML prediction
