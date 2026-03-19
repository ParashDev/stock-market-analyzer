"""01_clean.py - Fetch and clean market data
Sources: yfinance (S&P 500 prices + fundamentals), FRED (macro indicators)
Outputs: daily_prices.csv, fundamentals.csv, macro.csv
"""

import sys
import time
import io
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


# ── S&P 500 Ticker List ───────────────────────────────────────────────

def fetch_sp500_tickers():
    """Fetch S&P 500 constituents from Wikipedia."""
    print("== Fetching S&P 500 constituents ==")
    try:
        resp = requests.get(config.SP500_WIKI_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        tables = pd.read_html(io.StringIO(resp.text))
        df = tables[0]
        df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)

        tickers = df["Symbol"].tolist()
        meta = {}
        for _, row in df.iterrows():
            sym = row["Symbol"]
            meta[sym] = {
                "name": row.get("Security", sym),
                "sector": row.get("GICS Sector", "Unknown"),
                "industry": row.get("GICS Sub-Industry", "Unknown"),
            }

        print(f"   {len(tickers)} constituents loaded")
        return tickers, meta
    except Exception as e:
        print(f"   WARNING: Wikipedia fetch failed: {e}")
        print("   Using fallback list (top 100)")
        return _fallback_tickers()


def _fallback_tickers():
    stocks = {
        "AAPL": ("Apple Inc.", "Information Technology"), "MSFT": ("Microsoft Corp.", "Information Technology"),
        "AMZN": ("Amazon.com Inc.", "Consumer Discretionary"), "NVDA": ("NVIDIA Corp.", "Information Technology"),
        "GOOGL": ("Alphabet Inc.", "Communication Services"), "META": ("Meta Platforms", "Communication Services"),
        "BRK-B": ("Berkshire Hathaway", "Financials"), "TSLA": ("Tesla Inc.", "Consumer Discretionary"),
        "UNH": ("UnitedHealth Group", "Health Care"), "LLY": ("Eli Lilly", "Health Care"),
        "JPM": ("JPMorgan Chase", "Financials"), "XOM": ("Exxon Mobil", "Energy"),
        "V": ("Visa Inc.", "Financials"), "JNJ": ("Johnson & Johnson", "Health Care"),
        "PG": ("Procter & Gamble", "Consumer Staples"), "MA": ("Mastercard", "Financials"),
        "AVGO": ("Broadcom Inc.", "Information Technology"), "HD": ("Home Depot", "Consumer Discretionary"),
        "MRK": ("Merck & Co.", "Health Care"), "COST": ("Costco Wholesale", "Consumer Staples"),
        "ABBV": ("AbbVie Inc.", "Health Care"), "PEP": ("PepsiCo Inc.", "Consumer Staples"),
        "ADBE": ("Adobe Inc.", "Information Technology"), "KO": ("Coca-Cola Co.", "Consumer Staples"),
        "CRM": ("Salesforce Inc.", "Information Technology"), "WMT": ("Walmart Inc.", "Consumer Staples"),
        "CSCO": ("Cisco Systems", "Information Technology"), "TMO": ("Thermo Fisher", "Health Care"),
        "ACN": ("Accenture plc", "Information Technology"), "MCD": ("McDonald's Corp.", "Consumer Discretionary"),
        "LIN": ("Linde plc", "Materials"), "ABT": ("Abbott Labs", "Health Care"),
        "NFLX": ("Netflix Inc.", "Communication Services"), "AMD": ("Advanced Micro Devices", "Information Technology"),
        "DHR": ("Danaher Corp.", "Health Care"), "ORCL": ("Oracle Corp.", "Information Technology"),
        "TXN": ("Texas Instruments", "Information Technology"), "PM": ("Philip Morris", "Consumer Staples"),
        "NEE": ("NextEra Energy", "Utilities"), "UPS": ("United Parcel Service", "Industrials"),
        "RTX": ("RTX Corp.", "Industrials"), "INTC": ("Intel Corp.", "Information Technology"),
        "QCOM": ("Qualcomm Inc.", "Information Technology"), "BA": ("Boeing Co.", "Industrials"),
        "AMGN": ("Amgen Inc.", "Health Care"), "LOW": ("Lowe's Cos.", "Consumer Discretionary"),
        "SBUX": ("Starbucks Corp.", "Consumer Discretionary"), "CAT": ("Caterpillar Inc.", "Industrials"),
        "GS": ("Goldman Sachs", "Financials"), "BLK": ("BlackRock Inc.", "Financials"),
        "DE": ("Deere & Co.", "Industrials"), "ISRG": ("Intuitive Surgical", "Health Care"),
        "MDLZ": ("Mondelez Int'l", "Consumer Staples"), "GILD": ("Gilead Sciences", "Health Care"),
        "SYK": ("Stryker Corp.", "Health Care"), "ADP": ("ADP Inc.", "Industrials"),
        "BKNG": ("Booking Holdings", "Consumer Discretionary"), "VRTX": ("Vertex Pharma", "Health Care"),
        "ADI": ("Analog Devices", "Information Technology"), "MMC": ("Marsh & McLennan", "Financials"),
        "REGN": ("Regeneron Pharma", "Health Care"), "LRCX": ("Lam Research", "Information Technology"),
        "PANW": ("Palo Alto Networks", "Information Technology"), "SCHW": ("Charles Schwab", "Financials"),
        "KLAC": ("KLA Corp.", "Information Technology"), "BSX": ("Boston Scientific", "Health Care"),
        "CB": ("Chubb Ltd.", "Financials"), "ETN": ("Eaton Corp.", "Industrials"),
        "SNPS": ("Synopsys Inc.", "Information Technology"), "MO": ("Altria Group", "Consumer Staples"),
        "SO": ("Southern Co.", "Utilities"), "CME": ("CME Group", "Financials"),
        "DUK": ("Duke Energy", "Utilities"), "SHW": ("Sherwin-Williams", "Materials"),
        "PLD": ("Prologis Inc.", "Real Estate"), "PGR": ("Progressive Corp.", "Financials"),
        "CI": ("Cigna Group", "Health Care"), "ICE": ("Intercontinental Exchange", "Financials"),
        "CL": ("Colgate-Palmolive", "Consumer Staples"), "EOG": ("EOG Resources", "Energy"),
        "NOC": ("Northrop Grumman", "Industrials"), "ZTS": ("Zoetis Inc.", "Health Care"),
        "MCK": ("McKesson Corp.", "Health Care"), "WM": ("Waste Management", "Industrials"),
        "USB": ("U.S. Bancorp", "Financials"), "CVS": ("CVS Health", "Health Care"),
        "FDX": ("FedEx Corp.", "Industrials"), "BDX": ("Becton Dickinson", "Health Care"),
        "SLB": ("Schlumberger", "Energy"), "PYPL": ("PayPal Holdings", "Financials"),
        "CMG": ("Chipotle Mexican Grill", "Consumer Discretionary"), "APD": ("Air Products", "Materials"),
        "ORLY": ("O'Reilly Automotive", "Consumer Discretionary"), "EMR": ("Emerson Electric", "Industrials"),
        "GD": ("General Dynamics", "Industrials"), "MSI": ("Motorola Solutions", "Information Technology"),
        "PNC": ("PNC Financial", "Financials"), "AJG": ("Arthur J. Gallagher", "Financials"),
        "HUM": ("Humana Inc.", "Health Care"), "NSC": ("Norfolk Southern", "Industrials"),
        "CTAS": ("Cintas Corp.", "Industrials"), "MAR": ("Marriott Int'l", "Consumer Discretionary"),
        "TGT": ("Target Corp.", "Consumer Discretionary"), "ROP": ("Roper Technologies", "Industrials"),
        "WELL": ("Welltower Inc.", "Real Estate"), "SPG": ("Simon Property", "Real Estate"),
    }
    tickers = list(stocks.keys())
    meta = {t: {"name": n, "sector": s, "industry": s} for t, (n, s) in stocks.items()}
    return tickers, meta


# ── Price Data ─────────────────────────────────────────────────────────

def fetch_daily_prices(tickers):
    """Batch-download daily OHLCV from yfinance. Returns long-format DataFrame."""
    print(f"== Downloading daily prices ({len(tickers)} tickers, 1 year) ==")
    try:
        raw = yf.download(
            tickers,
            period="1y",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"   ERROR: Price download failed: {e}")
        sys.exit(1)

    if raw.empty:
        print("   ERROR: No price data returned")
        sys.exit(1)

    frames = []
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df_t = raw.copy()
            else:
                df_t = raw.xs(ticker, level=1, axis=1).copy()

            if df_t.dropna(how="all").empty:
                continue

            df_t = df_t.reset_index()
            df_t.columns = [str(c).lower() for c in df_t.columns]
            df_t["ticker"] = ticker

            keep = [c for c in ["date", "ticker", "open", "high", "low", "close", "volume"] if c in df_t.columns]
            df_t = df_t[keep].dropna(subset=["close"])
            frames.append(df_t)
        except (KeyError, TypeError):
            continue

    if not frames:
        print("   ERROR: Could not parse any ticker data")
        sys.exit(1)

    prices = pd.concat(frames, ignore_index=True)
    prices["date"] = pd.to_datetime(prices["date"]).dt.strftime("%Y-%m-%d")
    prices = prices.sort_values(["ticker", "date"]).reset_index(drop=True)

    # Round numeric columns
    for col in ["open", "high", "low", "close"]:
        if col in prices.columns:
            prices[col] = prices[col].round(2)

    n_tickers = prices["ticker"].nunique()
    n_days = prices["date"].nunique()
    print(f"   {n_tickers} tickers x {n_days} trading days = {len(prices):,} rows")
    return prices


# ── Fundamentals ───────────────────────────────────────────────────────

def fetch_fundamentals(tickers, wiki_meta):
    """Fetch per-ticker fundamentals via yfinance .info calls."""
    print(f"== Fetching fundamentals ({len(tickers)} tickers) ==")
    print("   This takes ~10 minutes (one API call per ticker)...")
    records = []
    failed = 0
    start_time = time.time()

    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed * 60
            remaining = (len(tickers) - i - 1) / rate if rate > 0 else 0
            print(f"   {i + 1}/{len(tickers)} ({rate:.0f}/min, ~{remaining:.0f} min left)")

        meta = wiki_meta.get(ticker, {})
        row = {
            "ticker": ticker,
            "name": meta.get("name", ticker),
            "sector": meta.get("sector", "Unknown"),
            "industry": meta.get("industry", "Unknown"),
        }

        try:
            info = yf.Ticker(ticker).info or {}
            row.update({
                "current_price":  info.get("currentPrice") or info.get("regularMarketPrice"),
                "target_mean":    info.get("targetMeanPrice"),
                "target_low":     info.get("targetLowPrice"),
                "target_high":    info.get("targetHighPrice"),
                "recommendation": info.get("recommendationKey"),
                "num_analysts":   info.get("numberOfAnalystOpinions"),
                "market_cap":     info.get("marketCap"),
                "pe_ratio":       info.get("trailingPE"),
                "forward_pe":     info.get("forwardPE"),
                "dividend_yield": info.get("dividendYield"),
                "week52_high":    info.get("fiftyTwoWeekHigh"),
                "week52_low":     info.get("fiftyTwoWeekLow"),
            })
        except Exception:
            failed += 1

        records.append(row)
        time.sleep(0.1)

    df = pd.DataFrame(records)
    loaded = df["current_price"].notna().sum()
    elapsed = time.time() - start_time
    print(f"   Done in {elapsed / 60:.1f} min: {loaded} with full data, {failed} API failures")
    return df


# ── Macro Indicators ──────────────────────────────────────────────────

def fetch_macro():
    """Fetch VIX, Treasury yields, Fed funds rate from FRED."""
    if not config.FRED_API_KEY:
        print("== Skipping macro data (no FRED_API_KEY) ==")
        return pd.DataFrame()

    print("== Fetching macro indicators from FRED ==")
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    series_frames = {}
    for name, series_id in config.FRED_SERIES.items():
        try:
            resp = requests.get(
                f"{config.FRED_BASE}/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": config.FRED_API_KEY,
                    "file_type": "json",
                    "observation_start": start,
                    "observation_end": end,
                    "sort_order": "desc",
                    "limit": 30,
                },
                timeout=15,
            )
            resp.raise_for_status()
            obs = resp.json().get("observations", [])

            data = []
            for o in obs:
                if o["value"] != ".":
                    data.append({"date": o["date"], name: float(o["value"])})

            if data:
                series_frames[name] = pd.DataFrame(data)
                print(f"   {name}: {data[0][name]}")
        except Exception as e:
            print(f"   WARNING: {name} failed: {e}")

    if not series_frames:
        return pd.DataFrame()

    merged = None
    for name, df in series_frames.items():
        if merged is None:
            merged = df
        else:
            merged = merged.merge(df, on="date", how="outer")

    merged = merged.sort_values("date", ascending=False).reset_index(drop=True)
    print(f"   {len(merged)} days of macro data")
    return merged


# ── Main ───────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("STOCK MARKET ANALYZER - Data Fetch & Clean")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    tickers, wiki_meta = fetch_sp500_tickers()

    # Load custom watchlist
    watchlist_file = config.ROOT / "watchlist.txt"
    if watchlist_file.exists():
        custom = []
        for line in watchlist_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                sym = line.upper().replace(".", "-")
                if sym not in tickers:
                    custom.append(sym)
        if custom:
            print(f"== Adding {len(custom)} watchlist tickers: {', '.join(custom)} ==")
            tickers.extend(custom)
            # Fetch name/sector from yfinance for watchlist stocks
            for sym in custom:
                if sym not in wiki_meta:
                    try:
                        info = yf.Ticker(sym).info or {}
                        wiki_meta[sym] = {
                            "name": info.get("longName") or info.get("shortName") or sym,
                            "sector": info.get("sector") or "Unknown",
                            "industry": info.get("industry") or "Unknown",
                        }
                    except Exception:
                        wiki_meta[sym] = {"name": sym, "sector": "Watchlist", "industry": "Unknown"}

    prices = fetch_daily_prices(tickers)

    # Filter to tickers with enough history
    counts = prices.groupby("ticker").size()
    valid = counts[counts >= config.MIN_TRADING_DAYS].index.tolist()
    prices = prices[prices["ticker"].isin(valid)]
    print(f"   {len(valid)} tickers with >= {config.MIN_TRADING_DAYS} trading days")

    fundamentals = fetch_fundamentals(valid, wiki_meta)
    macro = fetch_macro()

    # Fetch hourly SPY data for catalyst timeline
    print("== Fetching hourly SPY data ==")
    try:
        spy_hourly = yf.download("SPY", period="5d", interval="1h", progress=False)
        if not spy_hourly.empty:
            spy_df = spy_hourly.reset_index()
            spy_df.columns = [str(c[0]).lower() if isinstance(c, tuple) else str(c).lower() for c in spy_df.columns]
            spy_df["datetime"] = pd.to_datetime(spy_df["datetime"]).dt.tz_convert(config.TIMEZONE).dt.strftime("%Y-%m-%d %I:%M %p")
            spy_df = spy_df.rename(columns={"datetime": "time"})
            spy_df = spy_df[["time", "open", "high", "low", "close", "volume"]].round(2)
            spy_df.to_csv(config.CLEANED_DIR / "spy_hourly.csv", index=False)
            print(f"   {len(spy_df)} hourly bars")
        else:
            print("   No SPY data returned")
    except Exception as e:
        print(f"   WARNING: SPY hourly fetch failed: {e}")

    # Save
    prices.to_csv(config.CLEANED_DIR / "daily_prices.csv", index=False)
    fundamentals.to_csv(config.CLEANED_DIR / "fundamentals.csv", index=False)
    if not macro.empty:
        macro.to_csv(config.CLEANED_DIR / "macro.csv", index=False)

    print()
    print("== Output ==")
    print(f"   daily_prices.csv  : {len(prices):>8,} rows")
    print(f"   fundamentals.csv  : {len(fundamentals):>8,} rows")
    print(f"   macro.csv         : {len(macro):>8,} rows")
    print("== Done ==")


if __name__ == "__main__":
    main()
