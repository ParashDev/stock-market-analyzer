"""02_fetch_news.py - Fetch news and sentiment from Finnhub
Optional enrichment - pipeline continues without it.
Outputs: market_news.csv, company_news.csv, earnings_calendar.csv
"""

import sys
import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def score_sentiment(text):
    """Keyword-based sentiment scoring. Returns -1 to +1."""
    if not text:
        return 0.0
    words = set(text.lower().split())
    pos = len(words & config.POSITIVE_WORDS)
    neg = len(words & config.NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 2)


def _finnhub_get(endpoint, params):
    """Helper for Finnhub API calls with auth."""
    params["token"] = config.FINNHUB_API_KEY
    resp = requests.get(f"{config.FINNHUB_BASE}/{endpoint}", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_market_news():
    """Fetch general market news."""
    print("== Fetching market news ==")
    try:
        articles = _finnhub_get("news", {"category": "general"})
        if not articles:
            print("   No market news returned")
            return pd.DataFrame()

        rows = []
        for a in articles[:100]:
            headline = a.get("headline", "")
            summary = a.get("summary", "")
            rows.append({
                "datetime": datetime.fromtimestamp(a.get("datetime", 0)).strftime("%Y-%m-%d %I:%M %p"),
                "headline": headline,
                "source": a.get("source", ""),
                "url": a.get("url", ""),
                "category": a.get("category", ""),
                "summary": summary[:300],
                "sentiment": score_sentiment(f"{headline} {summary}"),
            })

        df = pd.DataFrame(rows)
        pos = (df["sentiment"] > 0).sum()
        neg = (df["sentiment"] < 0).sum()
        print(f"   {len(df)} articles ({pos} positive, {neg} negative)")
        return df
    except Exception as e:
        print(f"   WARNING: Market news failed: {e}")
        return pd.DataFrame()


def fetch_company_news(tickers):
    """Fetch company-specific news for top movers."""
    print(f"== Fetching company news ({len(tickers)} tickers) ==")
    today = datetime.now().strftime("%Y-%m-%d")
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    all_rows = []
    for i, ticker in enumerate(tickers):
        try:
            articles = _finnhub_get("company-news", {
                "symbol": ticker,
                "from": two_days_ago,
                "to": today,
            })

            for a in articles[:5]:
                headline = a.get("headline", "")
                summary = a.get("summary", "")
                all_rows.append({
                    "datetime": datetime.fromtimestamp(a.get("datetime", 0)).strftime("%Y-%m-%d %I:%M %p"),
                    "ticker": ticker,
                    "headline": headline,
                    "source": a.get("source", ""),
                    "url": a.get("url", ""),
                    "summary": summary[:300],
                    "sentiment": score_sentiment(f"{headline} {summary}"),
                })

            time.sleep(0.5)  # 60 calls/min free tier
        except Exception:
            continue

        if (i + 1) % 10 == 0:
            print(f"   {i + 1}/{len(tickers)}...")

    df = pd.DataFrame(all_rows)
    print(f"   {len(df)} company articles fetched")
    return df


def fetch_earnings_calendar():
    """Fetch upcoming earnings from Finnhub."""
    print("== Fetching earnings calendar ==")
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        data = _finnhub_get("calendar/earnings", {"from": today, "to": next_week})
        events = data.get("earningsCalendar", [])

        if not events:
            print("   No upcoming earnings")
            return pd.DataFrame()

        rows = []
        for e in events:
            rows.append({
                "date": e.get("date", ""),
                "ticker": e.get("symbol", ""),
                "hour": e.get("hour", ""),
                "estimate_eps": e.get("epsEstimate"),
                "revenue_estimate": e.get("revenueEstimate"),
            })

        df = pd.DataFrame(rows)
        print(f"   {len(df)} earnings events in next 7 days")
        return df
    except Exception as e:
        print(f"   WARNING: Earnings calendar failed: {e}")
        return pd.DataFrame()


def fetch_past_earnings():
    """Fetch past 90 days of earnings results from Finnhub."""
    print("== Fetching past earnings results ==")
    try:
        ninety_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        data = _finnhub_get("calendar/earnings", {"from": ninety_ago, "to": yesterday})
        events = data.get("earningsCalendar", [])

        if not events:
            print("   No past earnings data")
            return pd.DataFrame()

        rows = []
        for e in events:
            actual = e.get("epsActual")
            estimate = e.get("epsEstimate")
            if actual is not None and estimate is not None:
                surprise_pct = ((actual - estimate) / abs(estimate) * 100) if estimate != 0 else 0
                rows.append({
                    "date": e.get("date", ""),
                    "ticker": e.get("symbol", ""),
                    "eps_actual": actual,
                    "eps_estimate": estimate,
                    "surprise_pct": round(surprise_pct, 2),
                    "revenue_actual": e.get("revenueActual"),
                    "revenue_estimate": e.get("revenueEstimate"),
                })

        df = pd.DataFrame(rows)
        print(f"   {len(df)} past earnings with actual results")
        return df
    except Exception as e:
        print(f"   WARNING: Past earnings failed: {e}")
        return pd.DataFrame()


def identify_top_movers():
    """Read daily prices and return top movers by absolute change."""
    prices_csv = config.CLEANED_DIR / "daily_prices.csv"
    if not prices_csv.exists():
        print("   WARNING: daily_prices.csv not found - skipping company news")
        return []

    try:
        prices = pd.read_csv(prices_csv)
        latest_date = prices["date"].max()
        dates = sorted(prices["date"].unique())
        if len(dates) < 2:
            return []

        prev_date = dates[-2]
        today_df = prices[prices["date"] == latest_date][["ticker", "close"]].rename(columns={"close": "today_close"})
        prev_df = prices[prices["date"] == prev_date][["ticker", "close"]].rename(columns={"close": "prev_close"})

        merged = today_df.merge(prev_df, on="ticker")
        merged["abs_change"] = ((merged["today_close"] / merged["prev_close"]) - 1).abs() * 100
        movers = merged.nlargest(config.NEWS_TOP_MOVERS, "abs_change")["ticker"].tolist()

        print(f"   Top {len(movers)} movers identified")
        return movers
    except Exception as e:
        print(f"   WARNING: Could not identify movers: {e}")
        return []


def main():
    if not config.FINNHUB_API_KEY:
        print("=" * 60)
        print("SKIPPING NEWS FETCH - no FINNHUB_API_KEY set")
        print("Pipeline continues without news data.")
        print("=" * 60)
        return

    print("=" * 60)
    print("STOCK MARKET ANALYZER - News & Sentiment")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    market_news = fetch_market_news()

    top_movers = identify_top_movers()
    company_news = fetch_company_news(top_movers) if top_movers else pd.DataFrame()

    earnings = fetch_earnings_calendar()
    past_earnings = fetch_past_earnings()

    # Save
    if not market_news.empty:
        market_news.to_csv(config.CLEANED_DIR / "market_news.csv", index=False)
    if not company_news.empty:
        company_news.to_csv(config.CLEANED_DIR / "company_news.csv", index=False)
    if not earnings.empty:
        earnings.to_csv(config.CLEANED_DIR / "earnings_calendar.csv", index=False)
    if not past_earnings.empty:
        past_earnings.to_csv(config.CLEANED_DIR / "past_earnings.csv", index=False)

    print()
    print("== Output ==")
    print(f"   market_news.csv       : {len(market_news):>6} articles")
    print(f"   company_news.csv      : {len(company_news):>6} articles")
    print(f"   earnings_calendar.csv : {len(earnings):>6} events")
    print(f"   past_earnings.csv     : {len(past_earnings):>6} results")
    print("== Done ==")


if __name__ == "__main__":
    main()
