"""Daily AI Momentum Brief — runs after US market close Mon–Fri.

Email layout (3 levels in one scroll):
  L1 — Layer summary row  (5 cells: Silicon / Infra / Connectivity / Platform / Apps)
  L2 — Theme heat map     (22 colour-coded cells, grouped by layer)
  L3 — Drill-down         (top 3 themes by |1D return|, ticker table + LLM commentary)
  Footer — link to interactive dashboard
"""
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.themes import THEME_BY_ID
from data.fetcher import fetch_theme_returns, layer_aggregates, top_movers
from shared.html import _pct, _price, _md_to_html, layer_summary_row, theme_heatmap, theme_returns_table, _TD, _TD_L, _TH, _TH_L
from shared.llm import groq_call
from shared.email_sender import send_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DASHBOARD_URL = "https://isaactwr-lang.github.io/ai-momentum/"

# ── LLM ───────────────────────────────────────────────────────────────────────

_DRILL_SYSTEM = """You are a terse quantitative equity analyst. You will receive performance data for up to 3 AI sub-themes that moved the most today.

For EACH theme write exactly 2–3 sentences of plain-English commentary explaining:
- What drove the move (catalyst, macro read-through, or sector rotation)
- What to watch next

Rules:
- Be specific — name companies, data points, or events where relevant
- No generic filler ("the market saw", "investors reacted")
- Output valid JSON only: {"theme_id": "commentary", ...}
- No markdown, no HTML in the JSON values"""


def _drilldown_commentary(movers: list, theme_returns: dict) -> dict:
    snippets = []
    for tid in movers:
        data = theme_returns[tid]
        agg  = data["aggregate"]
        tickers_str = ", ".join(
            f"{t}: {d['daily']:+.2f}%" if d else f"{t}: N/A"
            for t, d in data["tickers"].items() if d
        )
        snippets.append(
            f'{data["name"]} ({data["layer"]}): aggregate 1D {agg["daily"]:+.2f}%, '
            f'1W {agg["weekly"]:+.2f}% | tickers: {tickers_str}'
        )
    user_msg = "\n".join(snippets)
    try:
        raw = groq_call(_DRILL_SYSTEM, user_msg, max_tokens=600, json_mode=True)
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"LLM drill-down failed: {e}")
        return {}


# ── HTML builders ─────────────────────────────────────────────────────────────

def _drilldown_section(movers: list, theme_returns: dict, commentary: dict) -> str:
    html = '<h3 style="color:#1a3a5c;margin-top:24px">🔥 Top Movers — Drill-Down</h3>'
    for tid in movers:
        data  = theme_returns[tid]
        theme = THEME_BY_ID[tid]
        agg   = data["aggregate"]
        sign  = "+" if (agg["daily"] or 0) >= 0 else ""
        color = "#16a34a" if (agg["daily"] or 0) >= 0 else "#dc2626"
        daily_str = f'&nbsp;{sign}{agg["daily"]:.2f}%' if agg["daily"] is not None else "—"

        html += (
            f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:4px;'
            f'padding:14px 16px;margin-bottom:12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<span style="font-weight:700;font-size:15px;color:#1a3a5c">{theme["name"]}</span>'
            f'<span style="font-size:14px;font-weight:700;color:{color}">{daily_str}</span>'
            f'</div>'
            f'<div style="font-size:11px;color:#9ca3af;margin-bottom:8px">'
            f'{theme["layer"]} · {theme["thesis"]}</div>'
        )
        html += theme_returns_table(data, title="")
        note = commentary.get(tid, "")
        if note:
            html += f'<p style="font-size:13px;margin:10px 0 0;color:#374151">{note}</p>'
        html += '</div>'
    return html


def build_email(theme_returns: dict, date_str: str) -> str:
    layer_aggs = layer_aggregates(theme_returns)
    movers     = top_movers(theme_returns, n=3, key="daily")
    commentary = _drilldown_commentary(movers, theme_returns)

    l1    = layer_summary_row(layer_aggs, key="daily")
    l2    = theme_heatmap(theme_returns, key="daily", cols=4)
    l3    = _drilldown_section(movers, theme_returns, commentary)

    return f"""<html>
<body style="font-family:Arial,sans-serif;max-width:720px;margin:auto;color:#222;line-height:1.6;">

  <div style="background:#1a3a5c;color:#fff;padding:18px 24px;border-radius:6px 6px 0 0;">
    <h2 style="margin:0;font-size:20px;">⚡ AI Momentum — Daily Brief</h2>
    <p style="margin:4px 0 0;font-size:13px;opacity:0.8;">{date_str} &nbsp;·&nbsp; After US Close</p>
  </div>

  <div style="padding:20px 24px;background:#f9fafb;border:1px solid #e5e7eb;border-top:none;">

    <h3 style="color:#1a3a5c;margin-top:0">📊 Layer Performance</h3>
    {l1}

    <h3 style="color:#1a3a5c;margin-top:16px">🗺️ Theme Heat Map — 1D Return</h3>
    {l2}

    {l3}

    <hr style="margin-top:28px;border:none;border-top:1px solid #e5e7eb;">
    <p style="font-size:12px;color:#9ca3af;margin:12px 0 0;">
      <a href="{DASHBOARD_URL}" style="color:#1a3a5c;font-weight:600;">→ View interactive dashboard</a>
      &nbsp;·&nbsp; 22 themes · ~110 tickers · equal-weight aggregates
      &nbsp;·&nbsp; Data via Yahoo Finance
    </p>
  </div>

</body>
</html>"""


def run() -> None:
    sgt      = pytz.timezone("Asia/Singapore")
    date_str = datetime.now(sgt).strftime("%B %d, %Y")
    subject  = f"⚡ AI Momentum — Daily Brief · {date_str}"

    as_of = None
    as_of_str = os.getenv("RUN_AS_OF", "").strip()
    if as_of_str:
        try:
            as_of = date.fromisoformat(as_of_str)
            logger.info(f"Backdated run: {as_of}")
        except ValueError:
            logger.warning(f"Invalid RUN_AS_OF='{as_of_str}' — ignored")

    logger.info("Fetching theme returns...")
    theme_returns = fetch_theme_returns(as_of)

    logger.info("Building email...")
    html = build_email(theme_returns, date_str)

    send_email(subject, html)
    logger.info("Daily brief complete.")


if __name__ == "__main__":
    run()
