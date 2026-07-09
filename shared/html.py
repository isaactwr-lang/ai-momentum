"""HTML formatting helpers for AI Momentum emails and dashboard."""
import re
from typing import Dict, List, Optional, Tuple

_GREEN = "#16a34a"
_RED   = "#dc2626"
_GRAY  = "#6b7280"
_TH    = "background:#1a3a5c;color:#fff;padding:6px 10px;text-align:right;white-space:nowrap;"
_TH_L  = "background:#1a3a5c;color:#fff;padding:6px 10px;text-align:left;"
_TD    = "padding:5px 10px;border-bottom:1px solid #e5e7eb;text-align:right;"
_TD_L  = "padding:5px 10px;border-bottom:1px solid #e5e7eb;text-align:left;"


def _pct(val: Optional[float], decimals: int = 2) -> str:
    if val is None:
        return '<span style="color:#9ca3af">—</span>'
    sign  = "+" if val >= 0 else ""
    color = _GREEN if val > 0 else (_RED if val < 0 else _GRAY)
    return f'<span style="color:{color};font-weight:600">{sign}{val:.{decimals}f}%</span>'


def _price(val: Optional[float]) -> str:
    if val is None:
        return "—"
    if val >= 10_000:
        return f"{val:,.0f}"
    if val >= 10:
        return f"{val:,.2f}"
    return f"{val:.4f}"


def _md_to_html(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*',     r'<em>\1</em>', text, flags=re.DOTALL)
    text = re.sub(r'<p>\s*(&nbsp;)?\s*</p>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>\s*<br\s*/?>', '', text, flags=re.IGNORECASE)
    return text


def theme_returns_table(theme_data: Dict, title: str, key: str = "daily") -> str:
    """Render a per-ticker returns table for a single theme."""
    header = (
        f'<h4 style="color:#1a3a5c;margin:12px 0 4px">{title}</h4>'
        '<table style="border-collapse:collapse;width:100%;font-size:13px">'
        f'<thead><tr>'
        f'<th style="{_TH_L}">Ticker</th>'
        f'<th style="{_TH}">Last</th>'
        f'<th style="{_TH}">1D %</th>'
        f'<th style="{_TH}">1W %</th>'
        f'<th style="{_TH}">1M %</th>'
        f'<th style="{_TH}">YTD %</th>'
        f'<th style="{_TH}">1Y %</th>'
        f'</tr></thead><tbody>'
    )
    body = ""
    for ticker, d in theme_data["tickers"].items():
        if d:
            body += (
                f'<tr><td style="{_TD_L}"><b>{ticker}</b></td>'
                f'<td style="{_TD}">{_price(d["last"])}</td>'
                f'<td style="{_TD}">{_pct(d.get("daily"))}</td>'
                f'<td style="{_TD}">{_pct(d.get("weekly"))}</td>'
                f'<td style="{_TD}">{_pct(d.get("one_month"))}</td>'
                f'<td style="{_TD}">{_pct(d.get("ytd"))}</td>'
                f'<td style="{_TD}">{_pct(d.get("one_year"))}</td></tr>'
            )
        else:
            body += (
                f'<tr><td style="{_TD_L}"><b>{ticker}</b></td>'
                f'<td style="{_TD};color:#9ca3af;" colspan="6">data unavailable</td></tr>'
            )
    return header + body + "</tbody></table>"


def layer_summary_row(layer_aggs: Dict[str, Dict], key: str = "daily") -> str:
    """Render a single-row layer summary bar."""
    cells = ""
    for layer, agg in layer_aggs.items():
        val = agg.get(key)
        sign  = "+" if (val or 0) >= 0 else ""
        color = _GREEN if (val or 0) > 0 else (_RED if (val or 0) < 0 else _GRAY)
        val_str = f'{sign}{val:.2f}%' if val is not None else "—"
        cells += (
            f'<td style="padding:10px 14px;text-align:center;border-right:1px solid #e5e7eb;">'
            f'<div style="font-size:11px;color:#6b7280;font-weight:600">{layer}</div>'
            f'<div style="font-size:16px;color:{color};font-weight:700;margin-top:3px">{val_str}</div>'
            f'</td>'
        )
    return (
        '<table style="border-collapse:collapse;width:100%;background:#fff;'
        'border:1px solid #e5e7eb;border-radius:4px;margin-bottom:16px">'
        f'<tr>{cells}</tr></table>'
    )


def theme_heatmap(theme_returns: Dict, key: str = "daily", cols: int = 4) -> str:
    """Render a colour-coded heat map of all themes, grouped by layer."""
    from config.themes import LAYERS, THEMES_BY_LAYER

    valid = {
        tid: data
        for tid, data in theme_returns.items()
        if data["aggregate"].get(key) is not None
    }
    if not valid:
        return ""

    values = [data["aggregate"][key] for data in valid.values()]
    cap    = max(abs(v) for v in values) or 1.0

    def _cell_colors(val: float) -> tuple:
        t = max(-1.0, min(1.0, val / cap))
        if t >= 0:
            r = round(250 - t * (250 - 21))
            g = round(250 - t * (250 - 128))
            b = round(250 - t * (250 - 61))
        else:
            t = -t
            r = round(250 - t * (250 - 185))
            g = round(250 - t * (250 - 28))
            b = round(250 - t * (250 - 28))
        bg     = f"#{r:02x}{g:02x}{b:02x}"
        bright = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        fg     = "#1f2937" if bright > 0.60 else "#ffffff"
        return bg, fg

    cell_base = "padding:10px 4px;text-align:center;border:3px solid #f3f4f6;"
    rows_html = ""

    for layer in LAYERS:
        layer_themes = [t for t in THEMES_BY_LAYER[layer] if t["id"] in valid]
        if not layer_themes:
            continue
        # layer label spanning full width
        rows_html += (
            f'<tr><td colspan="{cols}" style="padding:6px 8px;background:#1a3a5c;'
            f'color:#fff;font-size:11px;font-weight:700;letter-spacing:0.05em">'
            f'{layer.upper()}</td></tr>'
        )
        for i in range(0, len(layer_themes), cols):
            chunk = layer_themes[i: i + cols]
            rows_html += "<tr>"
            for theme in chunk:
                data = valid[theme["id"]]
                val  = data["aggregate"][key]
                bg, fg = _cell_colors(val)
                sign = "+" if val >= 0 else ""
                rows_html += (
                    f'<td style="{cell_base}background:{bg};width:{100//cols}%">'
                    f'<div style="font-size:9px;font-weight:700;font-family:Arial,sans-serif;color:{fg}">'
                    f'{theme["name"]}</div>'
                    f'<div style="font-size:13px;font-family:Arial,sans-serif;margin-top:4px;color:{fg}">'
                    f'{sign}{val:.2f}%</div>'
                    f'</td>'
                )
            for _ in range(cols - len(chunk)):
                rows_html += f'<td style="{cell_base}background:#f9fafb"></td>'
            rows_html += "</tr>"

    label = "1D" if key == "daily" else "1W"
    return (
        '<table style="width:100%;border-collapse:collapse;table-layout:fixed">'
        f'{rows_html}</table>'
        f'<p style="font-size:10px;color:#9ca3af;margin:4px 0 0">'
        f'{label} return · green = positive · red = negative · equal-weight per theme</p>'
    )
