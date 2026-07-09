"""News scrapers for AI Momentum weekly digest.

Each scraper returns a list of plain-text snippets (max ~300 chars each).
Theme routing: which source feeds which theme ids.
"""
import logging
import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Which source feeds which theme ids
SOURCE_THEME_MAP: Dict[str, List[str]] = {
    "semianalysis":    ["ai_accelerators", "custom_silicon", "semis_equipment", "ai_memory", "foundry_packaging", "eda_ip"],
    "dcdy":            ["dc_compute", "ai_networking", "optical", "ai_servers", "dc_power_cooling"],
    "canary":          ["power_gen", "nuclear", "grid_infra"],
    "utilitydive":     ["power_gen", "grid_infra", "dc_power_cooling"],
    "tomshardware":    ["ai_accelerators", "ai_servers", "ai_memory"],
    "electronicdesign":["power_semis", "eda_ip", "custom_silicon"],
}


def _scrape(url: str, label: str, max_chars: int = 5000) -> str:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body
        lines = [l.strip() for l in main.get_text(separator="\n").splitlines() if l.strip()]
        text  = "\n".join(lines)
        return text[:max_chars] if len(text) > max_chars else text
    except Exception as e:
        logger.warning(f"[{label}] scrape failed: {e}")
        return ""


def _snippets(text: str, max_per_source: int = 8) -> List[str]:
    """Split text into sentence-ish snippets, filter noise, cap at max_per_source."""
    if not text:
        return []
    # Split on newlines and sentence boundaries
    raw = re.split(r"\n+|(?<=[.!?])\s+", text)
    out = []
    for s in raw:
        s = s.strip()
        if len(s) < 40 or len(s) > 500:
            continue
        if re.search(r"(cookie|privacy|subscribe|sign up|log in|newsletter)", s, re.I):
            continue
        out.append(s)
        if len(out) >= max_per_source:
            break
    return out


def fetch_semianalysis() -> List[str]:
    text = _scrape("https://www.semianalysis.com", "SemiAnalysis")
    return _snippets(text)


def fetch_dcdy() -> List[str]:
    text = _scrape("https://www.datacenterdynamics.com/en/news/", "DatacenterDynamics")
    return _snippets(text)


def fetch_canary() -> List[str]:
    text = _scrape("https://canarymedianews.com/category/clean-energy/", "CanaryMedia")
    return _snippets(text)


def fetch_utilitydive() -> List[str]:
    text = _scrape("https://www.utilitydive.com/news/", "UtilityDive")
    return _snippets(text)


def fetch_tomshardware() -> List[str]:
    text = _scrape("https://www.tomshardware.com/tech-industry/artificial-intelligence", "TomsHardware")
    return _snippets(text)


def fetch_electronicdesign() -> List[str]:
    text = _scrape("https://www.electronicdesign.com/technologies/power", "ElectronicDesign")
    return _snippets(text)


_FETCHERS = {
    "semianalysis":     fetch_semianalysis,
    "dcdy":             fetch_dcdy,
    "canary":           fetch_canary,
    "utilitydive":      fetch_utilitydive,
    "tomshardware":     fetch_tomshardware,
    "electronicdesign": fetch_electronicdesign,
}


def fetch_all_news() -> Dict[str, List[str]]:
    """Returns dict keyed by theme_id → list of news snippet strings."""
    theme_snippets: Dict[str, List[str]] = {}
    for source_key, fetcher in _FETCHERS.items():
        snippets = fetcher()
        if not snippets:
            continue
        for tid in SOURCE_THEME_MAP.get(source_key, []):
            theme_snippets.setdefault(tid, []).extend(snippets)
    # Deduplicate and cap per theme
    return {tid: list(dict.fromkeys(snips))[:12] for tid, snips in theme_snippets.items()}
