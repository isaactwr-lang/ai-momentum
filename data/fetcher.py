"""Fetch per-ticker and per-theme returns for the AI momentum tracker.

Theme aggregate = equal-weight average across constituent tickers.
Tickers that fail to resolve are silently excluded from the average.
"""
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.themes import THEMES, LAYERS, THEMES_BY_LAYER

logger = logging.getLogger(__name__)


# ── yfinance helpers (ported from weekly-market-recap) ────────────────────────

def _clip(closes: pd.Series, as_of: Optional[date]) -> pd.Series:
    if as_of is None:
        return closes
    tz = closes.index.tz
    cutoff = pd.Timestamp(as_of + timedelta(days=1), tz=tz) if tz else pd.Timestamp(as_of + timedelta(days=1))
    return closes[closes.index < cutoff]


def _prior_week_base(closes: pd.Series) -> float:
    last_date = closes.index[-1].date()
    week_start = last_date - timedelta(days=last_date.weekday())
    tz = closes.index.tz
    cutoff = pd.Timestamp(week_start, tz=tz) if tz else pd.Timestamp(week_start)
    prior = closes[closes.index < cutoff]
    return float(prior.iloc[-1]) if not prior.empty else float(closes.iloc[0])


def _returns(ticker: str, as_of: Optional[date] = None) -> Optional[Dict]:
    """Return last price + daily / weekly / 1M / YTD / 1Y % for a ticker."""
    try:
        hist = yf.Ticker(ticker).history(period="2y", auto_adjust=True)
        if hist.empty or len(hist) < 2:
            return None
        closes = _clip(hist["Close"].dropna(), as_of)
        if len(closes) < 2:
            return None
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2])

        daily         = (last / prev - 1) * 100
        week_base     = _prior_week_base(closes)
        one_month_base = float(closes.iloc[max(0, len(closes) - 22)])
        one_year_base  = float(closes.iloc[max(0, len(closes) - 252)])

        weekly    = (last / week_base      - 1) * 100
        one_month = (last / one_month_base - 1) * 100
        one_year  = (last / one_year_base  - 1) * 100

        ytd_start = closes[closes.index.year == (as_of or date.today()).year]
        ytd_base  = float(ytd_start.iloc[0]) if not ytd_start.empty else float(closes.iloc[0])
        ytd = (last / ytd_base - 1) * 100

        return {
            "last": round(last, 4),
            "daily": round(daily, 2),
            "weekly": round(weekly, 2),
            "one_month": round(one_month, 2),
            "ytd": round(ytd, 2),
            "one_year": round(one_year, 2),
        }
    except Exception as e:
        logger.warning(f"yfinance [{ticker}]: {e}")
        return None


# ── Theme aggregation ─────────────────────────────────────────────────────────

def _avg(values: List[Optional[float]]) -> Optional[float]:
    valid = [v for v in values if v is not None]
    return round(sum(valid) / len(valid), 2) if valid else None


def fetch_theme_returns(as_of: Optional[date] = None) -> Dict:
    """
    Returns dict keyed by theme id:
      {
        "aggregate": {daily, weekly, one_month, ytd, one_year},
        "tickers":   {TICKER: {last, daily, weekly, ...} or None},
      }
    """
    results = {}
    for theme in THEMES:
        ticker_data = {}
        for t in theme["tickers"]:
            ticker_data[t] = _returns(t, as_of)

        keys = ["daily", "weekly", "one_month", "ytd", "one_year"]
        aggregate = {
            k: _avg([d[k] for d in ticker_data.values() if d is not None])
            for k in keys
        }

        results[theme["id"]] = {
            "name":      theme["name"],
            "layer":     theme["layer"],
            "aggregate": aggregate,
            "tickers":   ticker_data,
        }

    return results


def layer_aggregates(theme_returns: Dict) -> Dict[str, Dict]:
    """Equal-weight aggregate of theme aggregates, grouped by layer."""
    out = {}
    for layer in LAYERS:
        layer_themes = THEMES_BY_LAYER[layer]
        keys = ["daily", "weekly", "one_month", "ytd", "one_year"]
        out[layer] = {
            k: _avg([
                theme_returns[t["id"]]["aggregate"].get(k)
                for t in layer_themes
                if t["id"] in theme_returns
            ])
            for k in keys
        }
    return out


def top_movers(theme_returns: Dict, n: int = 3, key: str = "daily") -> List[str]:
    """Return top n theme ids by absolute value of key (default: daily return)."""
    scored = [
        (tid, abs(data["aggregate"].get(key) or 0))
        for tid, data in theme_returns.items()
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [tid for tid, _ in scored[:n]]


# ── CLI verification ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("Fetching all 22 themes...\n")
    data = fetch_theme_returns()
    for tid, d in data.items():
        agg = d["aggregate"]
        resolved = sum(1 for v in d["tickers"].values() if v is not None)
        total    = len(d["tickers"])
        daily_str = f"{agg['daily']:+.2f}%" if agg["daily"] is not None else "N/A"
        weekly_str = f"{agg['weekly']:+.2f}%" if agg["weekly"] is not None else "N/A"
        print(f"  {d['name']:<30} 1D {daily_str:>8}  1W {weekly_str:>8}  ({resolved}/{total} tickers OK)")

    print("\nLayer aggregates:")
    layers = layer_aggregates(data)
    for layer, agg in layers.items():
        daily_str = f"{agg['daily']:+.2f}%" if agg["daily"] is not None else "N/A"
        print(f"  {layer:<20} {daily_str}")

    print("\nTop 3 movers (daily):", top_movers(data))
