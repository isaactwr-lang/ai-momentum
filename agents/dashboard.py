"""Generate docs/index.html — a self-contained interactive GitHub Pages dashboard.

All market data is embedded as JSON in a <script> tag.
Pure HTML/CSS/JS — no framework, no external dependencies.
Interaction: click layer → expand themes → click theme → expand tickers.
"""
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.themes import THEMES, LAYERS, THEMES_BY_LAYER
from data.fetcher import fetch_theme_returns, layer_aggregates, top_movers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DOCS_PATH = Path(__file__).parent.parent / "docs" / "index.html"


def _color(val):
    if val is None:
        return "#9ca3af"
    return "#16a34a" if val > 0 else ("#dc2626" if val < 0 else "#6b7280")


def _pct_str(val, decimals=2):
    if val is None:
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.{decimals}f}%"


def build_dashboard(theme_returns: dict, generated_at: str) -> str:
    layer_aggs = layer_aggregates(theme_returns)

    # Serialise all data for JS
    payload = {
        "generated_at": generated_at,
        "layers": {
            layer: {
                "daily":     layer_aggs[layer].get("daily"),
                "weekly":    layer_aggs[layer].get("weekly"),
                "one_month": layer_aggs[layer].get("one_month"),
                "ytd":       layer_aggs[layer].get("ytd"),
                "one_year":  layer_aggs[layer].get("one_year"),
            }
            for layer in LAYERS
        },
        "themes": {
            tid: {
                "name":    data["name"],
                "layer":   data["layer"],
                "thesis":  next((t["thesis"] for t in THEMES if t["id"] == tid), ""),
                "aggregate": data["aggregate"],
                "tickers": {
                    t: d for t, d in data["tickers"].items()
                },
            }
            for tid, data in theme_returns.items()
        },
        "layer_theme_ids": {
            layer: [t["id"] for t in THEMES_BY_LAYER[layer]]
            for layer in LAYERS
        },
    }
    data_json = json.dumps(payload, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Momentum Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; background: #f3f4f6; color: #1f2937; }}
  header {{ background: #1a3a5c; color: #fff; padding: 16px 24px; }}
  header h1 {{ font-size: 20px; }}
  header p  {{ font-size: 12px; opacity: 0.7; margin-top: 4px; }}
  .container {{ max-width: 960px; margin: 24px auto; padding: 0 16px; }}

  /* Breadcrumb */
  #breadcrumb {{ font-size: 12px; color: #6b7280; margin-bottom: 16px; }}
  #breadcrumb span {{ cursor: pointer; color: #1a3a5c; text-decoration: underline; }}

  /* Layer grid */
  .layer-grid {{ display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; margin-bottom: 20px; }}
  .layer-card {{
    background: #fff; border: 2px solid #e5e7eb; border-radius: 6px;
    padding: 14px 10px; text-align: center; cursor: pointer; transition: border-color 0.15s;
  }}
  .layer-card:hover, .layer-card.active {{ border-color: #1a3a5c; }}
  .layer-card .layer-name  {{ font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; }}
  .layer-card .layer-ret   {{ font-size: 22px; font-weight: 800; margin-top: 6px; }}

  /* Theme grid */
  #theme-panel {{ display: none; margin-bottom: 20px; }}
  #theme-panel h2 {{ font-size: 15px; color: #1a3a5c; margin-bottom: 12px; }}
  .theme-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; }}
  .theme-card {{
    border-radius: 4px; padding: 10px 8px; text-align: center;
    cursor: pointer; border: 2px solid transparent; transition: border-color 0.15s;
  }}
  .theme-card:hover, .theme-card.active {{ border-color: #fff; }}
  .theme-card .theme-name {{ font-size: 9px; font-weight: 700; line-height: 1.3; }}
  .theme-card .theme-ret  {{ font-size: 14px; font-weight: 800; margin-top: 4px; }}

  /* Ticker panel */
  #ticker-panel {{ display: none; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 16px; }}
  #ticker-panel h2 {{ font-size: 15px; color: #1a3a5c; margin-bottom: 4px; }}
  #ticker-panel .thesis {{ font-size: 12px; color: #6b7280; margin-bottom: 12px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th {{ background: #1a3a5c; color: #fff; padding: 6px 10px; text-align: right; white-space: nowrap; }}
  th:first-child {{ text-align: left; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #e5e7eb; text-align: right; }}
  td:first-child {{ text-align: left; font-weight: 700; }}
  .pos {{ color: #16a34a; font-weight: 600; }}
  .neg {{ color: #dc2626; font-weight: 600; }}
  .neu {{ color: #6b7280; }}
  .footer {{ font-size: 11px; color: #9ca3af; text-align: center; margin-top: 32px; padding-bottom: 24px; }}

  @media (max-width: 600px) {{
    .layer-grid  {{ grid-template-columns: repeat(2,1fr); }}
    .theme-grid  {{ grid-template-columns: repeat(2,1fr); }}
  }}
</style>
</head>
<body>

<header>
  <h1>⚡ AI Momentum Dashboard</h1>
  <p>22 themes · ~110 tickers · equal-weight aggregates · updated {generated_at}</p>
</header>

<div class="container">
  <div id="breadcrumb">
    <span onclick="resetAll()">All Layers</span>
    <span id="bc-layer" style="display:none"> › <span id="bc-layer-name" onclick="showLayer(currentLayer)"></span></span>
    <span id="bc-theme" style="display:none"> › <span id="bc-theme-name"></span></span>
  </div>

  <div class="layer-grid" id="layer-grid"></div>

  <div id="theme-panel">
    <h2 id="theme-panel-title"></h2>
    <div class="theme-grid" id="theme-grid"></div>
  </div>

  <div id="ticker-panel">
    <h2 id="ticker-title"></h2>
    <p class="thesis" id="ticker-thesis"></p>
    <table id="ticker-table"></table>
  </div>

  <div class="footer">
    Data via Yahoo Finance &nbsp;·&nbsp;
    <a href="https://github.com/isaactwr-lang/ai-momentum" style="color:#1a3a5c;">GitHub</a>
    &nbsp;·&nbsp; Refreshed daily after US close
  </div>
</div>

<script>
const DATA = {data_json};

let currentLayer = null;
let currentTheme = null;

function pct(v, d=2) {{
  if (v == null) return '<span class="neu">—</span>';
  const sign = v >= 0 ? '+' : '';
  const cls  = v > 0 ? 'pos' : (v < 0 ? 'neg' : 'neu');
  return `<span class="${{cls}}">${{sign}}${{v.toFixed(d)}}%</span>`;
}}

function heatColor(val, cap) {{
  if (val == null) return ['#e5e7eb', '#6b7280'];
  const t = Math.max(-1, Math.min(1, val / (cap || 1)));
  let r, g, b;
  if (t >= 0) {{
    r = Math.round(250 - t*(250-21));
    g = Math.round(250 - t*(250-128));
    b = Math.round(250 - t*(250-61));
  }} else {{
    const tt = -t;
    r = Math.round(250 - tt*(250-185));
    g = Math.round(250 - tt*(250-28));
    b = Math.round(250 - tt*(250-28));
  }}
  const bright = (0.299*r + 0.587*g + 0.114*b) / 255;
  const fg = bright > 0.60 ? '#1f2937' : '#ffffff';
  return [`rgb(${{r}},${{g}},${{b}})`, fg];
}}

function resetAll() {{
  currentLayer = null; currentTheme = null;
  document.getElementById('theme-panel').style.display  = 'none';
  document.getElementById('ticker-panel').style.display = 'none';
  document.getElementById('bc-layer').style.display = 'none';
  document.getElementById('bc-theme').style.display = 'none';
  document.querySelectorAll('.layer-card').forEach(c => c.classList.remove('active'));
}}

function showLayer(layerName) {{
  currentLayer = layerName; currentTheme = null;
  document.getElementById('ticker-panel').style.display = 'none';
  document.getElementById('bc-theme').style.display = 'none';
  document.querySelectorAll('.layer-card').forEach(c => {{
    c.classList.toggle('active', c.dataset.layer === layerName);
  }});
  // breadcrumb
  document.getElementById('bc-layer').style.display = '';
  document.getElementById('bc-layer-name').textContent = layerName;

  const themeIds = DATA.layer_theme_ids[layerName] || [];
  const vals = themeIds.map(id => DATA.themes[id]?.aggregate?.daily).filter(v => v != null);
  const cap  = vals.length ? Math.max(...vals.map(Math.abs)) : 1;

  const grid = document.getElementById('theme-grid');
  grid.innerHTML = themeIds.map(id => {{
    const t   = DATA.themes[id];
    const val = t?.aggregate?.daily;
    const [bg, fg] = heatColor(val, cap);
    const sign = (val||0) >= 0 ? '+' : '';
    const valStr = val != null ? `${{sign}}${{val.toFixed(2)}}%` : '—';
    return `<div class="theme-card" data-tid="${{id}}"
      style="background:${{bg}};color:${{fg}}"
      onclick="showTickers('${{id}}')">
      <div class="theme-name">${{t.name}}</div>
      <div class="theme-ret">${{valStr}}</div>
    </div>`;
  }}).join('');

  document.getElementById('theme-panel-title').textContent = layerName + ' — Themes';
  document.getElementById('theme-panel').style.display = 'block';
}}

function showTickers(themeId) {{
  currentTheme = themeId;
  const t = DATA.themes[themeId];
  document.querySelectorAll('.theme-card').forEach(c => c.classList.toggle('active', c.dataset.tid === themeId));
  // breadcrumb
  document.getElementById('bc-theme').style.display = '';
  document.getElementById('bc-theme-name').textContent = t.name;

  document.getElementById('ticker-title').textContent  = t.name;
  document.getElementById('ticker-thesis').textContent = t.thesis;

  let rows = `<tr>
    <th>Ticker</th><th>Last</th><th>1D %</th><th>1W %</th>
    <th>1M %</th><th>YTD %</th><th>1Y %</th>
  </tr>`;
  for (const [ticker, d] of Object.entries(t.tickers)) {{
    if (!d) {{
      rows += `<tr><td>${{ticker}}</td><td colspan="6" class="neu">data unavailable</td></tr>`;
      continue;
    }}
    const fmt = v => v >= 10000 ? v.toLocaleString('en',{{maximumFractionDigits:0}})
                   : v >= 10    ? v.toFixed(2)
                   : v.toFixed(4);
    rows += `<tr>
      <td>${{ticker}}</td>
      <td>${{fmt(d.last)}}</td>
      <td>${{pct(d.daily)}}</td>
      <td>${{pct(d.weekly)}}</td>
      <td>${{pct(d.one_month)}}</td>
      <td>${{pct(d.ytd)}}</td>
      <td>${{pct(d.one_year)}}</td>
    </tr>`;
  }}
  // Aggregate row
  const agg = t.aggregate;
  rows += `<tr style="background:#f0f4f8;font-weight:700">
    <td>AGGREGATE</td><td>—</td>
    <td>${{pct(agg.daily)}}</td>
    <td>${{pct(agg.weekly)}}</td>
    <td>${{pct(agg.one_month)}}</td>
    <td>${{pct(agg.ytd)}}</td>
    <td>${{pct(agg.one_year)}}</td>
  </tr>`;
  document.getElementById('ticker-table').innerHTML = rows;
  document.getElementById('ticker-panel').style.display = 'block';
}}

// ── Init: render layer cards ────────────────────────────────────────────────
(function init() {{
  const grid = document.getElementById('layer-grid');
  const layerVals = Object.values(DATA.layers).map(l => l.daily).filter(v => v != null);
  const cap = layerVals.length ? Math.max(...layerVals.map(Math.abs)) : 1;

  grid.innerHTML = Object.entries(DATA.layers).map(([layer, agg]) => {{
    const val = agg.daily;
    const [bg, fg] = heatColor(val, cap);
    const sign = (val||0) >= 0 ? '+' : '';
    const valStr = val != null ? `${{sign}}${{val.toFixed(2)}}%` : '—';
    return `<div class="layer-card" data-layer="${{layer}}" onclick="showLayer('${{layer}}')"
      style="border-color:#e5e7eb">
      <div class="layer-name">${{layer}}</div>
      <div class="layer-ret" style="color:${{val > 0 ? '#16a34a' : val < 0 ? '#dc2626' : '#6b7280'}}">${{valStr}}</div>
    </div>`;
  }}).join('');
}})();
</script>
</body>
</html>"""


def run() -> None:
    sgt          = pytz.timezone("Asia/Singapore")
    generated_at = datetime.now(sgt).strftime("%b %d, %Y %H:%M SGT")

    as_of = None
    as_of_str = os.getenv("RUN_AS_OF", "").strip()
    if as_of_str:
        try:
            as_of = date.fromisoformat(as_of_str)
        except ValueError:
            pass

    logger.info("Fetching theme returns for dashboard...")
    theme_returns = fetch_theme_returns(as_of)

    html = build_dashboard(theme_returns, generated_at)
    DOCS_PATH.write_text(html, encoding="utf-8")
    logger.info(f"Dashboard written to {DOCS_PATH}")


if __name__ == "__main__":
    run()
