"""Weekly AI Momentum Digest — runs every Monday 9 AM SGT.

Email structure:
  1. Header
  2. Executive heatmap (22 themes, 1W return)
  3. Per-theme sections sorted by 1W return (ticker table + LLM commentary)
  4. Cross-theme rotation narrative
  5. Footer
"""
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.themes import THEMES, THEME_BY_ID
from data.fetcher import fetch_theme_returns, layer_aggregates, top_movers
from data.news import fetch_all_news
from shared.html import (
    _pct, _price, _md_to_html, layer_summary_row,
    theme_heatmap, theme_returns_table, _TD, _TD_L, _TH, _TH_L,
)
from shared.llm import groq_call
from shared.email_sender import send_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DASHBOARD_URL = "https://isaactwr-lang.github.io/ai-momentum/"

# ── LLM prompts ───────────────────────────────────────────────────────────────

_THEME_SYSTEM = """You are a quantitative analyst writing a weekly commentary bullet for one AI sub-theme.

You receive:
- Performance data (1W, 1M, YTD, 1Y aggregate return + individual tickers)
- News snippets from relevant sources

Write 4–6 bullet points in HTML (<ul><li>...</li></ul>) covering:
- What drove weekly performance (specific companies, data points, catalysts)
- Any notable divergence between tickers in this theme
- Forward-looking read: what to watch next week
- One risk or headwind if relevant

Rules:
- Be specific — name tickers, percentages, events
- No generic filler
- Each bullet 1–2 sentences
- Start directly with <ul> — no preamble, no heading"""

_ROTATION_SYSTEM = """You are a macro-quant analyst writing the cross-theme rotation section of a weekly AI equity digest.

You receive aggregate 1W returns for all 22 AI sub-themes, grouped by layer.

Write 5–7 bullet points in HTML (<ul><li>...</li></ul>) identifying:
- Which layers led / lagged and what it signals about AI capex cycle positioning
- Largest divergences between themes (e.g., Foundry up while Equipment down)
- Any rotation signal between Infrastructure and Applications themes
- What the pattern collectively implies about where we are in the AI cycle

Rules:
- Reference specific theme names and return figures
- 1–2 sentences per bullet
- Start directly with <ul> — no preamble"""


# ── LLM calls ────────────────────────────────────────────────────────────────

def _theme_commentary(tid: str, data: dict, snippets: List[str]) -> str:
    agg = data["aggregate"]
    ticker_lines = "\n".join(
        f"  {t}: 1D {d['daily']:+.2f}% | 1W {d['weekly']:+.2f}% | 1M {d['one_month']:+.2f}% | YTD {d['ytd']:+.2f}%"
        if d else f"  {t}: data unavailable"
        for t, d in data["tickers"].items()
    )
    news_block = "\n".join(f"- {s}" for s in snippets[:8]) if snippets else "No news snippets available."
    user_msg = (
        f"Theme: {data['name']} ({data['layer']})\n"
        f"Thesis: {THEME_BY_ID[tid]['thesis']}\n\n"
        f"Aggregate: 1W {agg['weekly']:+.2f}% | 1M {agg['one_month']:+.2f}% | "
        f"YTD {agg['ytd']:+.2f}% | 1Y {agg['one_year']:+.2f}%\n\n"
        f"Tickers:\n{ticker_lines}\n\n"
        f"News:\n{news_block}"
    )
    try:
        return groq_call(_THEME_SYSTEM, user_msg, max_tokens=500)
    except Exception as e:
        logger.warning(f"LLM [{tid}]: {e}")
        return ""


def _rotation_commentary(theme_returns: dict) -> str:
    lines = []
    for layer in ["Silicon", "Infrastructure", "Connectivity", "Platform", "Applications"]:
        layer_themes = [t for t in THEMES if t["layer"] == layer]
        for t in layer_themes:
            agg = theme_returns[t["id"]]["aggregate"]
            w   = agg.get("weekly")
            lines.append(f"  {t['name']} ({layer}): 1W {w:+.2f}%" if w is not None else f"  {t['name']} ({layer}): N/A")
    user_msg = "Weekly returns by theme:\n" + "\n".join(lines)
    try:
        return groq_call(_ROTATION_SYSTEM, user_msg, max_tokens=700)
    except Exception as e:
        logger.warning(f"LLM rotation: {e}")
        return ""


# ── HTML builders ─────────────────────────────────────────────────────────────

def _theme_section(tid: str, data: dict, commentary: str) -> str:
    agg   = data["aggregate"]
    theme = THEME_BY_ID[tid]
    w_str = f'{agg["weekly"]:+.2f}%' if agg["weekly"] is not None else "—"
    color = "#16a34a" if (agg["weekly"] or 0) >= 0 else "#dc2626"

    html  = (
        f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:4px;'
        f'padding:14px 16px;margin-bottom:16px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'border-bottom:1px solid #e5e7eb;padding-bottom:8px;margin-bottom:10px">'
        f'<div>'
        f'<span style="font-weight:700;font-size:15px;color:#1a3a5c">{theme["name"]}</span>'
        f'<span style="font-size:11px;color:#9ca3af;margin-left:8px">{theme["layer"]}</span>'
        f'</div>'
        f'<span style="font-size:14px;font-weight:700;color:{color}">{w_str}</span>'
        f'</div>'
    )
    html += theme_returns_table(data, title="")
    if commentary:
        html += f'<div style="margin-top:12px;font-size:13px">{commentary}</div>'
    html += '</div>'
    return html


def build_email(theme_returns: dict, all_commentary: dict, rotation_html: str, date_str: str) -> str:
    layer_aggs = layer_aggregates(theme_returns)

    # Sort themes by 1W return descending
    sorted_ids = sorted(
        theme_returns.keys(),
        key=lambda tid: theme_returns[tid]["aggregate"].get("weekly") or 0,
        reverse=True,
    )

    l1       = layer_summary_row(layer_aggs, key="weekly")
    heatmap  = theme_heatmap(theme_returns, key="weekly", cols=4)
    sections = "".join(_theme_section(tid, theme_returns[tid], all_commentary.get(tid, "")) for tid in sorted_ids)

    return f"""<html>
<body style="font-family:Arial,sans-serif;max-width:720px;margin:auto;color:#222;line-height:1.6;">

  <div style="background:#1a3a5c;color:#fff;padding:18px 24px;border-radius:6px 6px 0 0;">
    <h2 style="margin:0;font-size:20px;">📋 AI Momentum — Weekly Digest</h2>
    <p style="margin:4px 0 0;font-size:13px;opacity:0.8;">Week of {date_str}</p>
  </div>

  <div style="padding:20px 24px;background:#f9fafb;border:1px solid #e5e7eb;border-top:none;">

    <h3 style="color:#1a3a5c;margin-top:0">📊 Layer Performance — 1W</h3>
    {l1}

    <h3 style="color:#1a3a5c;margin-top:16px">🗺️ Theme Heat Map — 1W Return</h3>
    {heatmap}

    <h3 style="color:#1a3a5c;margin-top:24px">🔄 Cross-Theme Rotation</h3>
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:4px;padding:14px 16px;margin-bottom:20px;font-size:13px;">
      {rotation_html}
    </div>

    <h3 style="color:#1a3a5c;margin-top:8px">📌 Theme Breakdown</h3>
    {sections}

    <hr style="margin-top:28px;border:none;border-top:1px solid #e5e7eb;">
    <p style="font-size:12px;color:#9ca3af;margin:12px 0 0;">
      <a href="{DASHBOARD_URL}" style="color:#1a3a5c;font-weight:600;">→ View interactive dashboard</a>
      &nbsp;·&nbsp; 22 themes · ~110 tickers · equal-weight aggregates
      &nbsp;·&nbsp; Data via Yahoo Finance
      &nbsp;·&nbsp; Commentary via Groq (Llama 3.3 70B)
    </p>
  </div>

</body>
</html>"""


def run() -> None:
    sgt      = pytz.timezone("Asia/Singapore")
    date_str = datetime.now(sgt).strftime("%B %d, %Y")
    subject  = f"📋 AI Momentum — Weekly Digest · {date_str}"

    as_of = None
    as_of_str = os.getenv("RUN_AS_OF", "").strip()
    if as_of_str:
        try:
            as_of = date.fromisoformat(as_of_str)
        except ValueError:
            pass

    logger.info("Fetching theme returns...")
    theme_returns = fetch_theme_returns(as_of)

    logger.info("Fetching news...")
    news = fetch_all_news()

    logger.info("Generating per-theme commentary (parallel)...")
    all_commentary: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_theme_commentary, tid, data, news.get(tid, [])): tid
            for tid, data in theme_returns.items()
        }
        for future in as_completed(futures):
            tid = futures[future]
            try:
                all_commentary[tid] = future.result()
            except Exception as e:
                logger.warning(f"Commentary [{tid}]: {e}")
                all_commentary[tid] = ""

    logger.info("Generating rotation commentary...")
    rotation_html = _rotation_commentary(theme_returns)

    logger.info("Building email...")
    html = build_email(theme_returns, all_commentary, rotation_html, date_str)

    send_email(subject, html)
    logger.info("Weekly digest complete.")


if __name__ == "__main__":
    run()
