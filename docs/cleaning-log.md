# Cleaning Decisions Log

## Decision 01: Ticker Format
BRK.B → BRK-B. yfinance uses dashes, Wikipedia uses dots. Normalize on download.

## Decision 02: Minimum Trading Days
Require 100+ trading days of history. Needed for 50-day MA calculation. Filters out recent IPOs and delistings.

## Decision 03: Price Rounding
All prices rounded to 2 decimal places. Volume kept as integer.

## Decision 04: NaN Handling in Fundamentals
If yfinance .info fails for a ticker, Wikipedia metadata (sector, name, industry) is used as fallback. Financial fields (target_mean, pe_ratio, etc.) remain null — downstream scoring handles nulls by assigning neutral scores.

## Decision 05: Sentiment Scoring
Simple keyword-based: count positive vs negative words in headline + summary, scale to [-1, +1]. Not sophisticated, but transparent and debuggable. No external NLP dependencies.

## Decision 06: FRED Missing Values
FRED returns "." for missing observations. Filter these out, keep only numeric values.

## Decision 07: Volume Spike Threshold
2x the 20-day average volume = "spike". Industry-standard heuristic.

## Decision 08: Analyst Upside Cap
Upside score capped at 100 (corresponding to 30%+ upside). Prevents micro-caps with absurd targets from dominating.

## Decision 09: Technical Score Baseline
Start at 50 (neutral), add/subtract based on signals. Ensures stocks with no signals get a middling score rather than zero.

## Decision 10: News Rate Limiting
0.5 second delay between Finnhub company-news calls. Free tier allows 60 calls/min. 50 tickers × 0.5s = 25 seconds.

## Decision 11: Scoring Weight Rebalancing
When news data is unavailable, the 15% news weight is redistributed to analyst_upside (+5%) and technical (+5%). Maintains total = 100%.

## Decision 12: Long-Format Price Storage
Prices stored as (date, ticker, OHLCV) rows instead of wide format. Cleaner for per-ticker groupby operations in transform.
