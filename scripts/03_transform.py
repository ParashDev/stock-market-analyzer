"""03_transform.py - Analyze, score, and rank stocks
Reads cleaned CSVs, calculates technicals, scores stocks, generates dashboard_data.json
"""

import sys
import json
import math
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


# ── Data Loading ───────────────────────────────────────────────────────

def load_csv(filename, required=False):
    path = config.CLEANED_DIR / filename
    if path.exists():
        df = pd.read_csv(path)
        print(f"   Loaded {filename}: {len(df)} rows")
        return df
    if required:
        print(f"   ERROR: Required file {filename} not found")
        sys.exit(1)
    print(f"   Optional {filename} not found - skipping")
    return pd.DataFrame()


def load_all():
    print("== Loading data ==")
    data = {
        "prices": load_csv("daily_prices.csv", required=True),
        "fundamentals": load_csv("fundamentals.csv", required=True),
        "macro": load_csv("macro.csv"),
        "market_news": load_csv("market_news.csv"),
        "company_news": load_csv("company_news.csv"),
        "earnings": load_csv("earnings_calendar.csv"),
    }
    data["past_earnings"] = load_csv("past_earnings.csv")
    data["has_news"] = not data["market_news"].empty
    data["has_macro"] = not data["macro"].empty
    data["has_earnings"] = not data["earnings"].empty
    data["has_past_earnings"] = not data["past_earnings"].empty
    return data


# ── Technical Indicators ───────────────────────────────────────────────

def calc_technicals(prices):
    """Calculate RSI, MACD, MAs, Bollinger, volume signals for each ticker."""
    print("== Calculating technical indicators ==")
    results = []
    tickers = prices["ticker"].unique()

    for ticker in tickers:
        df = prices[prices["ticker"] == ticker].sort_values("date").copy()
        if len(df) < config.MA_SHORT:
            continue

        close = df["close"].reset_index(drop=True)
        volume = df["volume"].reset_index(drop=True)
        n = len(close)

        # RSI
        rsi_series = RSIIndicator(close, window=config.RSI_PERIOD).rsi()

        # MACD
        macd_ind = MACD(close, window_slow=config.MACD_SLOW, window_fast=config.MACD_FAST, window_sign=config.MACD_SIGNAL)
        macd_hist = macd_ind.macd_diff()

        # Moving averages
        sma_short = SMAIndicator(close, window=config.MA_SHORT).sma_indicator()
        sma_long = SMAIndicator(close, window=config.MA_LONG).sma_indicator() if n >= config.MA_LONG else pd.Series([np.nan] * n)

        # Bollinger Bands
        bb = BollingerBands(close, window=config.BOLLINGER_PERIOD, window_dev=config.BOLLINGER_STD)

        # Volume average
        vol_avg = volume.rolling(window=config.VOLUME_AVG_PERIOD).mean()

        # Latest and previous values
        latest_close = close.iloc[-1]
        prev_close = close.iloc[-2] if n > 1 else latest_close
        latest_rsi = rsi_series.iloc[-1]
        latest_macd_hist = macd_hist.iloc[-1]
        prev_macd_hist = macd_hist.iloc[-2] if n > 1 else 0
        latest_sma_short = sma_short.iloc[-1]
        latest_sma_long = sma_long.iloc[-1]
        latest_vol = volume.iloc[-1]
        latest_vol_avg = vol_avg.iloc[-1]
        vol_ratio = latest_vol / latest_vol_avg if pd.notna(latest_vol_avg) and latest_vol_avg > 0 else 1.0

        # Price changes
        change_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if n > 1 else 0
        change_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if n > 5 else 0
        change_20d = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if n > 20 else 0

        # Signals
        rsi_oversold = bool(pd.notna(latest_rsi) and latest_rsi < config.RSI_OVERSOLD)
        rsi_overbought = bool(pd.notna(latest_rsi) and latest_rsi > config.RSI_OVERBOUGHT)
        macd_bullish_cross = bool(pd.notna(latest_macd_hist) and latest_macd_hist > 0 and prev_macd_hist <= 0)

        golden_cross = False
        death_cross = False
        if n >= config.MA_LONG and pd.notna(latest_sma_long):
            prev_short = sma_short.iloc[-2]
            prev_long = sma_long.iloc[-2]
            if pd.notna(prev_long):
                golden_cross = bool(latest_sma_short > latest_sma_long and prev_short <= prev_long)
                death_cross = bool(latest_sma_short < latest_sma_long and prev_short >= prev_long)

        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        below_lower_bb = bool(pd.notna(bb_lower) and latest_close < bb_lower)
        above_upper_bb = bool(pd.notna(bb_upper) and latest_close > bb_upper)
        volume_breakout = bool(vol_ratio >= config.VOLUME_SPIKE_THRESHOLD)

        year_low = float(close.min())
        year_high = float(close.max())
        near_52w_low = bool((latest_close / year_low - 1) < 0.05) if year_low > 0 else False

        def safe_round(v, decimals=2):
            if pd.isna(v) or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                return None
            return round(float(v), decimals)

        results.append({
            "ticker": ticker,
            "close": safe_round(latest_close),
            "prev_close": safe_round(prev_close),
            "change_1d": safe_round(change_1d),
            "change_5d": safe_round(change_5d),
            "change_20d": safe_round(change_20d),
            "volume": int(latest_vol) if pd.notna(latest_vol) else 0,
            "vol_avg_20d": int(latest_vol_avg) if pd.notna(latest_vol_avg) else 0,
            "vol_ratio": safe_round(vol_ratio),
            "rsi": safe_round(latest_rsi, 1),
            "macd_hist": safe_round(latest_macd_hist, 3),
            "sma_50": safe_round(latest_sma_short),
            "sma_200": safe_round(latest_sma_long),
            "bb_upper": safe_round(bb_upper),
            "bb_lower": safe_round(bb_lower),
            "year_high": safe_round(year_high),
            "year_low": safe_round(year_low),
            "rsi_oversold": rsi_oversold,
            "rsi_overbought": rsi_overbought,
            "macd_bullish_cross": macd_bullish_cross,
            "golden_cross": golden_cross,
            "death_cross": death_cross,
            "above_upper_bb": above_upper_bb,
            "below_lower_bb": below_lower_bb,
            "volume_breakout": volume_breakout,
            "near_52w_low": near_52w_low,
        })

    tech_df = pd.DataFrame(results)
    print(f"   Technicals for {len(tech_df)} stocks")
    return tech_df


# ── Scoring ────────────────────────────────────────────────────────────

def calc_scores(tech_df, fund_df, news_df):
    """Calculate composite upside score for each stock."""
    print("== Scoring stocks ==")
    has_news = not news_df.empty
    weights = config.WEIGHTS if has_news else config.WEIGHTS_NO_NEWS

    df = tech_df.merge(fund_df, on="ticker", how="left")

    # 1. Analyst Upside (0-100)
    df["upside_pct"] = np.where(
        (df["target_mean"].notna()) & (df["close"] > 0),
        ((df["target_mean"] / df["close"]) - 1) * 100,
        0,
    )
    df["score_analyst"] = np.clip(df["upside_pct"] / 30 * 100, 0, 100)

    # 2. Technical Score (0-100)
    ts = pd.Series(50.0, index=df.index)
    rsi = df["rsi"].fillna(50)
    ts += np.where(rsi < 30, 20, np.where(rsi < 40, 10, np.where(rsi > 70, -15, 0)))
    ts += np.where(df["macd_bullish_cross"], 15, 0)
    ts += np.where(df["golden_cross"], 15, 0)
    ts += np.where(df["sma_50"].notna() & (df["close"] > df["sma_50"]), 5, -5)
    ts += np.where(df["below_lower_bb"], 10, 0)
    df["score_technical"] = np.clip(ts, 0, 100)

    # 3. Momentum (0-100)
    mom = df["change_5d"].fillna(0) * 0.6 + df["change_20d"].fillna(0) * 0.4
    df["score_momentum"] = np.clip((mom + 10) / 20 * 100, 0, 100)

    # 4. Volume Signal (0-100)
    vr = df["vol_ratio"].fillna(1)
    df["score_volume"] = np.clip(
        np.where(vr >= 2.0, 70 + np.minimum(vr - 2.0, 3.0) * 10, vr / 2.0 * 70),
        0, 100,
    )

    # 5. News Sentiment (0-100)
    if has_news and "ticker" in news_df.columns:
        sent = news_df.groupby("ticker")["sentiment"].mean().reset_index()
        sent.columns = ["ticker", "avg_sentiment"]
        df = df.merge(sent, on="ticker", how="left")
        df["score_news"] = np.clip((df["avg_sentiment"].fillna(0) + 1) / 2 * 100, 0, 100)
    else:
        df["avg_sentiment"] = 0.0
        df["score_news"] = 50.0

    # Composite
    df["composite_score"] = (
        df["score_analyst"]   * weights.get("analyst_upside", 0) +
        df["score_technical"] * weights.get("technical", 0) +
        df["score_momentum"]  * weights.get("momentum", 0) +
        df["score_volume"]    * weights.get("volume_signal", 0) +
        df["score_news"]      * weights.get("news_sentiment", 0)
    ).round(1)

    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    print(f"   Scored {len(df)} stocks (top: {df['composite_score'].iloc[0]})")
    return df


# ── Reason Generator ──────────────────────────────────────────────────

def generate_reasons(row):
    reasons = []

    if pd.notna(row.get("upside_pct")) and row["upside_pct"] > 5:
        n = int(row["num_analysts"]) if pd.notna(row.get("num_analysts")) else 0
        a_str = f" ({n} analysts)" if n > 0 else ""
        reasons.append(f"Trading {row['upside_pct']:.1f}% below analyst target of ${row['target_mean']:.0f}{a_str}")

    if row.get("rsi_oversold"):
        reasons.append(f"RSI oversold at {row['rsi']:.1f} - potential bounce signal")
    elif row.get("rsi") and row["rsi"] < 40:
        reasons.append(f"RSI near oversold at {row['rsi']:.1f}")

    if row.get("macd_bullish_cross"):
        reasons.append("MACD bullish crossover - momentum shifting positive")

    if row.get("golden_cross"):
        reasons.append(f"Golden cross: 50-day MA (${row['sma_50']:.0f}) crossing above 200-day MA (${row['sma_200']:.0f})")

    if row.get("volume_breakout"):
        reasons.append(f"Volume spike: {row['vol_ratio']:.1f}x above 20-day average")

    if row.get("below_lower_bb"):
        reasons.append("Below lower Bollinger Band - statistically oversold")

    if row.get("near_52w_low"):
        pct = ((row["close"] / row["year_low"]) - 1) * 100
        reasons.append(f"Near 52-week low of ${row['year_low']:.2f} ({pct:.1f}% above)")

    if row.get("change_5d") and row["change_5d"] < -5:
        reasons.append(f"Down {abs(row['change_5d']):.1f}% in 5 days - oversold bounce candidate")
    elif row.get("change_5d") and row["change_5d"] > 5:
        reasons.append(f"Up {row['change_5d']:.1f}% in 5 days - strong momentum")

    if row.get("avg_sentiment") and row["avg_sentiment"] > 0.3:
        reasons.append("Positive news sentiment in recent headlines")

    if not reasons:
        reasons.append("Composite score above threshold across multiple factors")

    return reasons


# ── Scanners ───────────────────────────────────────────────────────────

def build_scanners(scored_df):
    print("== Building scanners ==")
    fields = ["ticker", "name", "sector", "close", "change_1d", "rsi", "vol_ratio", "composite_score"]

    def to_list(df, cols=None, max_n=20):
        cols = cols or fields
        available = [c for c in cols if c in df.columns]
        records = df.head(max_n)[available].to_dict("records")
        return _sanitize_records(records)

    scanners = {}

    mask = scored_df["rsi_oversold"] == True
    scanners["rsi_oversold"] = to_list(scored_df[mask].sort_values("rsi"))
    print(f"   RSI oversold: {len(scanners['rsi_oversold'])}")

    mask = scored_df["golden_cross"] == True
    scanners["golden_cross"] = to_list(scored_df[mask])
    print(f"   Golden cross: {len(scanners['golden_cross'])}")

    mask = scored_df["macd_bullish_cross"] == True
    scanners["macd_bullish"] = to_list(scored_df[mask])
    print(f"   MACD bullish: {len(scanners['macd_bullish'])}")

    mask = scored_df["volume_breakout"] == True
    scanners["volume_breakout"] = to_list(scored_df[mask].sort_values("vol_ratio", ascending=False))
    print(f"   Volume breakout: {len(scanners['volume_breakout'])}")

    mask = scored_df["below_lower_bb"] == True
    scanners["bollinger_oversold"] = to_list(scored_df[mask])
    print(f"   Bollinger oversold: {len(scanners['bollinger_oversold'])}")

    mask = scored_df["near_52w_low"] == True
    scanners["near_52w_low"] = to_list(scored_df[mask], cols=fields + ["year_low"])
    print(f"   Near 52-week low: {len(scanners['near_52w_low'])}")

    scanners["biggest_losers"] = to_list(scored_df.nsmallest(20, "change_1d"))
    scanners["biggest_gainers"] = to_list(scored_df.nlargest(20, "change_1d"))

    return scanners


# ── Market Summary ─────────────────────────────────────────────────────

def build_market_summary(scored_df, macro_df):
    total = len(scored_df)
    adv = int((scored_df["change_1d"] > 0).sum())
    dec = int((scored_df["change_1d"] < 0).sum())
    ratio = adv / total if total > 0 else 0.5

    summary = {
        "avg_change_pct": round(float(scored_df["change_1d"].mean()), 2),
        "median_change_pct": round(float(scored_df["change_1d"].median()), 2),
        "advancers": adv,
        "decliners": dec,
        "unchanged": total - adv - dec,
        "market_breadth": "bullish" if ratio > 0.65 else ("bearish" if ratio < 0.35 else "neutral"),
        "breadth_ratio": round(ratio, 2),
        "total_stocks": total,
    }

    if not macro_df.empty:
        latest = macro_df.iloc[0]
        for col in macro_df.columns:
            if col != "date" and pd.notna(latest.get(col)):
                summary[col] = round(float(latest[col]), 2)

    return summary


def build_sector_performance(scored_df):
    sectors = scored_df.groupby("sector").agg(
        avg_change=("change_1d", "mean"),
        stock_count=("ticker", "count"),
        advancers=("change_1d", lambda x: int((x > 0).sum())),
    ).reset_index()

    sectors["avg_change"] = sectors["avg_change"].round(2)
    sectors["color"] = sectors["sector"].map(config.SECTOR_COLORS).fillna("#6B7280")
    sectors = sectors.sort_values("avg_change", ascending=False)
    return _sanitize_records(sectors.to_dict("records"))


# ── JSON Helpers ───────────────────────────────────────────────────────

def _sanitize_value(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(float(v), 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


def _sanitize_records(records):
    out = []
    for r in records:
        out.append({k: _sanitize_value(v) for k, v in r.items()})
    return out


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    return _sanitize_value(obj)


# ── Dashboard JSON ─────────────────────────────────────────────────────

def build_dashboard(scored_df, data, scanners, market_summary, sector_perf):
    print("== Building dashboard JSON ==")
    latest_date = data["prices"]["date"].max()
    has_news = data["has_news"]
    weights = config.WEIGHTS if has_news else config.WEIGHTS_NO_NEWS

    # Top 50
    top50 = []
    for _, row in scored_df.head(config.TOP_N).iterrows():
        reasons = generate_reasons(row)
        top50.append({
            "rank": len(top50) + 1,
            "ticker": row["ticker"],
            "name": row.get("name", row["ticker"]),
            "sector": row.get("sector", "Unknown"),
            "price": row["close"],
            "change_1d": row["change_1d"],
            "change_5d": row.get("change_5d"),
            "change_20d": row.get("change_20d"),
            "target_mean": row.get("target_mean"),
            "upside_pct": row.get("upside_pct"),
            "composite_score": row.get("composite_score"),
            "score_analyst": row.get("score_analyst"),
            "score_technical": row.get("score_technical"),
            "score_momentum": row.get("score_momentum"),
            "score_volume": row.get("score_volume"),
            "rsi": row.get("rsi"),
            "macd_hist": row.get("macd_hist"),
            "sma_50": row.get("sma_50"),
            "sma_200": row.get("sma_200"),
            "vol_ratio": row.get("vol_ratio"),
            "pe_ratio": row.get("pe_ratio"),
            "market_cap": row.get("market_cap"),
            "recommendation": row.get("recommendation"),
            "sector_rank": int(row.get("sector_rank", 0)),
            "sector_count": int(row.get("sector_count", 0)),
            "sector_relative_score": row.get("sector_relative_score"),
            "sector_pe_avg": row.get("sector_pe_avg"),
            "annual_volatility": row.get("annual_volatility"),
            "sharpe_ratio": row.get("sharpe_ratio"),
            "max_drawdown_pct": row.get("max_drawdown_pct"),
            "return_1y": row.get("return_1y"),
            "year_high": row.get("year_high"),
            "year_low": row.get("year_low"),
            "bb_upper": row.get("bb_upper"),
            "bb_lower": row.get("bb_lower"),
            "reasons": reasons,
        })

    # News
    news = {"market": [], "company": []}
    if has_news:
        if not data["market_news"].empty:
            news["market"] = _sanitize_records(data["market_news"].head(30).to_dict("records"))
        if not data["company_news"].empty:
            news["company"] = _sanitize_records(data["company_news"].head(50).to_dict("records"))

    # Earnings — filter to our stocks and add company names
    earnings = []
    if data["has_earnings"] and not data["earnings"].empty:
        our_tickers = set(scored_df["ticker"].tolist())
        earn_df = data["earnings"]
        if "ticker" in earn_df.columns:
            earn_df = earn_df[earn_df["ticker"].isin(our_tickers)].copy()
            name_map = scored_df.set_index("ticker")["name"].to_dict()
            earn_df["name"] = earn_df["ticker"].map(name_map).fillna("")
        earnings = _sanitize_records(earn_df.head(30).to_dict("records"))

    dashboard = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_date": latest_date,
        "data_status": {
            "prices": True,
            "fundamentals": True,
            "news": has_news,
            "macro": data["has_macro"],
            "earnings": data["has_earnings"],
        },
        "market_summary": market_summary,
        "sector_performance": sector_perf,
        "top_50": top50,
        "scanners": scanners,
        "news": news,
        "earnings_calendar": earnings,
        "methodology": {
            "weights": weights,
            "factors": {
                "analyst_upside": "% below analyst consensus target price",
                "technical": "RSI, MACD crossovers, MA positioning, Bollinger Bands",
                "momentum": "5-day (60%) and 20-day (40%) price momentum",
                "volume_signal": "Volume vs 20-day average",
                "news_sentiment": "Keyword sentiment from recent headlines" if has_news else "Not available",
            },
        },
        "stats": {
            "total_analyzed": len(scored_df),
            "with_analyst_targets": int(scored_df["target_mean"].notna().sum()),
            "avg_score": round(float(scored_df["composite_score"].mean()), 1),
        },
    }

    return _sanitize(dashboard)


# ── Feature 1: Backtesting ─────────────────────────────────────────

def calc_backtest(prices, fund_df, news_df):
    """Simulate: if we bought our top 10 picks N days ago, how did they do?"""
    print("== Backtesting (20-day lookback) ==")
    dates = sorted(prices["date"].unique())
    lookback = config.BACKTEST_LOOKBACK_DAYS
    if len(dates) < lookback + config.MIN_TRADING_DAYS:
        print("   Not enough history for backtest")
        return {}

    sim_date = dates[-(lookback + 1)]
    end_date = dates[-1]

    # Get prices as of sim_date
    past_prices = prices[prices["date"] <= sim_date]
    past_tech = calc_technicals(past_prices)
    past_scored = calc_scores(past_tech, fund_df, news_df)
    top10 = past_scored.head(10)["ticker"].tolist()

    # Calculate returns for those picks
    picks = []
    for ticker in top10:
        t_prices = prices[prices["ticker"] == ticker].sort_values("date")
        sim_row = t_prices[t_prices["date"] == sim_date]
        end_row = t_prices[t_prices["date"] == end_date]
        if sim_row.empty or end_row.empty:
            continue
        start_p = float(sim_row["close"].iloc[0])
        end_p = float(end_row["close"].iloc[0])
        ret = (end_p / start_p - 1) * 100
        name = fund_df[fund_df["ticker"] == ticker]["name"].iloc[0] if ticker in fund_df["ticker"].values else ticker
        picks.append({"ticker": ticker, "name": name, "start_price": round(start_p, 2),
                       "end_price": round(end_p, 2), "return_pct": round(ret, 2)})

    # Benchmark: average of all stocks
    all_returns = []
    for ticker in prices["ticker"].unique():
        t_prices = prices[prices["ticker"] == ticker].sort_values("date")
        sim_row = t_prices[t_prices["date"] == sim_date]
        end_row = t_prices[t_prices["date"] == end_date]
        if sim_row.empty or end_row.empty:
            continue
        all_returns.append((float(end_row["close"].iloc[0]) / float(sim_row["close"].iloc[0]) - 1) * 100)

    port_ret = np.mean([p["return_pct"] for p in picks]) if picks else 0
    bench_ret = np.mean(all_returns) if all_returns else 0

    result = {
        "sim_start_date": sim_date,
        "sim_end_date": end_date,
        "lookback_days": lookback,
        "portfolio_return_pct": round(port_ret, 2),
        "benchmark_return_pct": round(bench_ret, 2),
        "outperformance_pct": round(port_ret - bench_ret, 2),
        "picks": picks,
    }
    print(f"   Portfolio: {port_ret:+.2f}% vs Benchmark: {bench_ret:+.2f}% ({port_ret - bench_ret:+.2f}%)")
    return result


# ── Feature 2: Sector-Relative Scoring ─────────────────────────────

def calc_sector_relative(scored_df):
    """Score each stock relative to its own sector peers."""
    print("== Calculating sector-relative scores ==")
    scored_df["sector_rank"] = 0
    scored_df["sector_count"] = 0
    scored_df["sector_relative_score"] = 50.0
    scored_df["sector_pe_avg"] = np.nan

    sector_leaders = {}
    for sector, group in scored_df.groupby("sector"):
        if len(group) < 3:
            continue
        # Rank within sector by composite score
        ranked = group.sort_values("composite_score", ascending=False).reset_index()
        for i, (idx, row) in enumerate(ranked.iterrows()):
            orig_idx = row["index"]
            scored_df.loc[orig_idx, "sector_rank"] = i + 1
            scored_df.loc[orig_idx, "sector_count"] = len(group)
            # Percentile within sector (higher = better)
            scored_df.loc[orig_idx, "sector_relative_score"] = round((1 - i / len(group)) * 100, 1)

        scored_df.loc[group.index, "sector_pe_avg"] = group["pe_ratio"].median()

        # Top 3 per sector
        top3 = ranked.head(3)
        sector_leaders[sector] = [
            {"ticker": r["ticker"], "name": r.get("name", r["ticker"]),
             "composite_score": r["composite_score"], "sector_relative_score": round((1 - i / len(group)) * 100, 1)}
            for i, (_, r) in enumerate(top3.iterrows())
        ]

    print(f"   Sector leaders for {len(sector_leaders)} sectors")
    return scored_df, _sanitize(sector_leaders)


# ── Feature 3: Earnings Impact Analysis ────────────────────────────

def calc_earnings_impact(prices, past_earnings_df):
    """Calculate average price move on earnings day for beats vs misses."""
    print("== Analyzing earnings impact ==")
    if past_earnings_df.empty or "ticker" not in past_earnings_df.columns:
        print("   No past earnings data")
        return {}

    our_tickers = set(prices["ticker"].unique())
    earn = past_earnings_df[past_earnings_df["ticker"].isin(our_tickers)].copy()
    if earn.empty:
        print("   No matching earnings events")
        return {}

    events = []
    for _, row in earn.iterrows():
        ticker = row["ticker"]
        date = row["date"]
        t_prices = prices[prices["ticker"] == ticker].sort_values("date")
        dates_list = t_prices["date"].tolist()
        if date not in dates_list:
            continue
        idx = dates_list.index(date)
        if idx == 0:
            continue
        price_before = float(t_prices.iloc[idx - 1]["close"])
        price_on = float(t_prices.iloc[idx]["close"])
        move_pct = (price_on / price_before - 1) * 100
        is_beat = row["eps_actual"] > row["eps_estimate"]

        events.append({
            "ticker": ticker, "date": date,
            "eps_actual": round(float(row["eps_actual"]), 2),
            "eps_estimate": round(float(row["eps_estimate"]), 2),
            "surprise_pct": round(float(row["surprise_pct"]), 1),
            "move_pct": round(move_pct, 2),
            "beat": is_beat,
        })

    if not events:
        return {}

    beats = [e for e in events if e["beat"]]
    misses = [e for e in events if not e["beat"]]

    result = {
        "total_events": len(events),
        "beat_count": len(beats),
        "miss_count": len(misses),
        "beat_rate_pct": round(len(beats) / len(events) * 100, 1) if events else 0,
        "avg_beat_move_pct": round(np.mean([e["move_pct"] for e in beats]), 2) if beats else 0,
        "avg_miss_move_pct": round(np.mean([e["move_pct"] for e in misses]), 2) if misses else 0,
        "recent_events": sorted(events, key=lambda x: x["date"], reverse=True)[:15],
    }
    print(f"   {len(events)} events: {len(beats)} beats (avg +{result['avg_beat_move_pct']}%), {len(misses)} misses (avg {result['avg_miss_move_pct']}%)")
    return _sanitize(result)


# ── Feature 4: Historical Accuracy Tracking ────────────────────────

def track_picks_accuracy(scored_df, prices):
    """Save today's top picks and evaluate past picks' performance."""
    print("== Tracking picks accuracy ==")
    history = []
    if config.PICKS_HISTORY_FILE.exists():
        try:
            with open(config.PICKS_HISTORY_FILE) as f:
                history = json.load(f)
        except Exception:
            history = []

    latest_date = prices["date"].max()
    dates = sorted(prices["date"].unique())

    # Evaluate past picks
    evaluated = []
    for entry in history:
        pick_date = entry["date"]
        if pick_date not in dates:
            continue
        pick_idx = dates.index(pick_date)
        days_since = len(dates) - 1 - pick_idx
        if days_since < 5:
            continue  # need at least 5 days

        wins = 0
        returns = []
        for p in entry["picks"]:
            t_prices = prices[prices["ticker"] == p["ticker"]].sort_values("date")
            end_row = t_prices[t_prices["date"] == latest_date]
            if end_row.empty:
                continue
            ret = (float(end_row["close"].iloc[0]) / p["price"] - 1) * 100
            returns.append(ret)
            if ret > 0:
                wins += 1

        if returns:
            evaluated.append({
                "date": pick_date, "days_held": days_since,
                "picks_count": len(returns), "win_count": wins,
                "win_rate": round(wins / len(returns) * 100, 1),
                "avg_return": round(np.mean(returns), 2),
            })

    # Current picks to save
    top10 = scored_df.head(10)
    current = {
        "date": latest_date,
        "picks": [{"ticker": r["ticker"], "price": r["close"]} for _, r in top10.iterrows()],
    }

    # Don't duplicate same date
    history = [h for h in history if h["date"] != latest_date]
    history.append(current)

    # Keep last 90 entries max
    history = history[-90:]

    with open(config.PICKS_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)

    all_wins = sum(e["win_count"] for e in evaluated)
    all_total = sum(e["picks_count"] for e in evaluated)
    all_returns = [e["avg_return"] for e in evaluated]

    result = {
        "total_picks_evaluated": all_total,
        "win_count": all_wins,
        "win_rate_pct": round(all_wins / all_total * 100, 1) if all_total > 0 else 0,
        "avg_return_pct": round(np.mean(all_returns), 2) if all_returns else 0,
        "history_entries": evaluated[-20:],
        "total_days_tracked": len(history),
        "first_run": all_total == 0,
    }
    print(f"   {all_total} past picks evaluated, win rate: {result['win_rate_pct']}%")
    return _sanitize(result)


# ── Feature 5: Risk Metrics ────────────────────────────────────────

def calc_risk_metrics(prices):
    """Calculate volatility, Sharpe ratio, max drawdown per stock."""
    print("== Calculating risk metrics ==")
    results = {}
    for ticker in prices["ticker"].unique():
        df = prices[prices["ticker"] == ticker].sort_values("date")
        close = df["close"].values
        if len(close) < 20:
            continue

        # Daily returns
        daily_ret = np.diff(close) / close[:-1]
        avg_ret = np.mean(daily_ret)
        vol = np.std(daily_ret)
        annual_vol = vol * np.sqrt(252)
        sharpe = (avg_ret / vol * np.sqrt(252)) if vol > 0 else 0

        # Max drawdown
        cummax = np.maximum.accumulate(close)
        drawdown = (close - cummax) / cummax
        max_dd = float(np.min(drawdown)) * 100

        # 1-year return
        ret_1y = (close[-1] / close[0] - 1) * 100

        results[ticker] = {
            "annual_volatility": round(annual_vol * 100, 1),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 1),
            "return_1y": round(ret_1y, 1),
        }

    print(f"   Risk metrics for {len(results)} stocks")
    return results


def main():
    print("=" * 60)
    print("STOCK MARKET ANALYZER - Analysis & Transform")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    data = load_all()
    tech_df = calc_technicals(data["prices"])
    scored_df = calc_scores(tech_df, data["fundamentals"], data.get("company_news", pd.DataFrame()))

    # Feature 2: Sector-relative scoring
    scored_df, sector_leaders = calc_sector_relative(scored_df)

    # Feature 5: Risk metrics
    risk = calc_risk_metrics(data["prices"])
    for idx, row in scored_df.iterrows():
        r = risk.get(row["ticker"], {})
        scored_df.loc[idx, "annual_volatility"] = r.get("annual_volatility", 0)
        scored_df.loc[idx, "sharpe_ratio"] = r.get("sharpe_ratio", 0)
        scored_df.loc[idx, "max_drawdown_pct"] = r.get("max_drawdown_pct", 0)
        scored_df.loc[idx, "return_1y"] = r.get("return_1y", 0)

    scanners = build_scanners(scored_df)
    market_summary = build_market_summary(scored_df, data["macro"])
    sector_perf = build_sector_performance(scored_df)

    # Feature 1: Backtesting
    backtest = calc_backtest(data["prices"], data["fundamentals"], data.get("company_news", pd.DataFrame()))

    # Feature 3: Earnings impact
    past_earn = load_csv("past_earnings.csv")
    earnings_impact = calc_earnings_impact(data["prices"], past_earn)

    # Feature 4: Historical accuracy
    accuracy = track_picks_accuracy(scored_df, data["prices"])

    dashboard = build_dashboard(scored_df, data, scanners, market_summary, sector_perf)
    dashboard["backtest"] = backtest
    dashboard["sector_leaders"] = sector_leaders
    dashboard["earnings_impact"] = earnings_impact
    dashboard["accuracy_tracking"] = accuracy

    # Add risk summary
    top50_risk = [risk.get(s["ticker"], {}) for s in dashboard["top_50"]]
    dashboard["risk_summary"] = {
        "avg_volatility": round(np.mean([r.get("annual_volatility", 0) for r in top50_risk]), 1),
        "avg_sharpe": round(np.mean([r.get("sharpe_ratio", 0) for r in top50_risk]), 2),
        "avg_drawdown": round(np.mean([r.get("max_drawdown_pct", 0) for r in top50_risk]), 1),
    }

    with open(config.DASHBOARD_JSON, "w") as f:
        json.dump(dashboard, f, indent=2, default=str)

    # Also write as JS for direct script-tag loading (no server needed)
    js_path = config.DATA_DIR / "dashboard_data.js"
    with open(js_path, "w") as f:
        f.write("window.__DASHBOARD_DATA__ = ")
        json.dump(dashboard, f, default=str)
        f.write(";")

    size_kb = config.DASHBOARD_JSON.stat().st_size / 1024
    print(f"\n== Output ==")
    print(f"   dashboard_data.json: {size_kb:.0f} KB")
    print(f"   #1: {dashboard['top_50'][0]['ticker']} (score {dashboard['top_50'][0]['composite_score']})")
    print(f"   Breadth: {dashboard['market_summary']['market_breadth']}")
    print("== Done ==")


if __name__ == "__main__":
    main()
