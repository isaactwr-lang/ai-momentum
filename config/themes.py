"""Single source of truth for all 22 AI momentum themes.

Organising principle: direct competitors (same customers, same product category)
belong in the same theme. Import THEMES wherever theme metadata is needed.
"""

from typing import List, TypedDict


class Theme(TypedDict):
    id: str
    name: str
    layer: str
    tickers: List[str]
    thesis: str


THEMES: List[Theme] = [
    # ── Layer 1: Silicon ──────────────────────────────────────────────────────
    {
        "id": "ai_accelerators",
        "name": "AI Accelerators",
        "layer": "Silicon",
        "tickers": ["NVDA", "AMD", "INTC", "CBRS"],
        "thesis": "Merchant GPU/AI chips competing for data center training sockets",
    },
    {
        "id": "custom_silicon",
        "name": "Custom Silicon & ASICs",
        "layer": "Silicon",
        "tickers": ["AVGO", "MRVL", "ARM", "QCOM", "MBLY", "NXPI"],
        "thesis": "Hyperscaler ASIC design wins, architecture licensing, edge/automotive NPUs",
    },
    {
        "id": "ai_memory",
        "name": "AI Memory",
        "layer": "Silicon",
        "tickers": ["MU", "000660.KS", "005930.KS", "WDC"],
        "thesis": "HBM and NAND supply for AI training clusters; HBM pricing cycle",
    },
    {
        "id": "semis_equipment",
        "name": "Semiconductor Equipment",
        "layer": "Silicon",
        "tickers": ["ASML", "AMAT", "LRCX", "KLAC", "ENTG", "MKSI"],
        "thesis": "Fab capital equipment rotating on AI-driven capex cycle with 12-18 month lag",
    },
    {
        "id": "eda_ip",
        "name": "EDA & Chip Design IP",
        "layer": "Silicon",
        "tickers": ["SNPS", "CDNS"],
        "thesis": "EDA software and IP licensing duopoly; every AI chip was designed on one of these",
    },
    {
        "id": "foundry_packaging",
        "name": "Foundry & Advanced Packaging",
        "layer": "Silicon",
        "tickers": ["TSM", "AMKR", "ASX", "UMC", "GFS"],
        "thesis": "TSM manufactures all leading AI chips; AMKR/ASX compete for CoWoS packaging",
    },
    {
        "id": "power_semis",
        "name": "Power Semiconductors",
        "layer": "Silicon",
        "tickers": ["MPWR", "VICR", "NVTS", "WOLF", "ON", "STM", "IFNNY"],
        "thesis": "48V direct-to-chip power delivery, GaN server PSUs, SiC power conversion for AI load",
    },

    # ── Layer 2: Physical Infrastructure ─────────────────────────────────────
    {
        "id": "ai_servers",
        "name": "AI Servers & Systems",
        "layer": "Infrastructure",
        "tickers": ["SMCI", "DELL", "HPE", "CLS", "PENG"],
        "thesis": "GPU server rack integrators and ODMs competing for the same cluster deployments",
    },
    {
        "id": "dc_compute",
        "name": "Data Center & AI Compute",
        "layer": "Infrastructure",
        "tickers": ["EQIX", "DLR", "CRWV", "IREN", "CORZ"],
        "thesis": "Colocation real estate (EQIX/DLR) vs GPU-as-a-service compute rental (CRWV/IREN/CORZ)",
    },
    {
        "id": "dc_power_cooling",
        "name": "DC Power & Cooling",
        "layer": "Infrastructure",
        "tickers": ["VRT", "ETN", "BE"],
        "thesis": "Data center UPS, power distribution, thermal management, and on-site fuel cell power",
    },
    {
        "id": "grid_infra",
        "name": "Grid Infrastructure",
        "layer": "Infrastructure",
        "tickers": ["GEV", "PWR", "EME", "MTZ", "HUBB", "AMSC"],
        "thesis": "Transformers, grid construction, and electrical hardware for AI power buildout",
    },
    {
        "id": "power_gen",
        "name": "Power Generation",
        "layer": "Infrastructure",
        "tickers": ["VST", "NRG", "CEG", "TLN"],
        "thesis": "Independent power producers competing for data center PPA contracts",
    },
    {
        "id": "nuclear",
        "name": "Nuclear Supply Chain",
        "layer": "Infrastructure",
        "tickers": ["CCJ", "OKLO", "LEU", "SMR", "NNE", "BWXT"],
        "thesis": "Uranium mining, enrichment, reactor components, and next-gen micro-reactors",
    },

    # ── Layer 3: Connectivity ─────────────────────────────────────────────────
    {
        "id": "optical",
        "name": "Optical Components",
        "layer": "Connectivity",
        "tickers": ["COHR", "LITE", "GLW", "AAOI"],
        "thesis": "Optical transceivers, lasers, and fiber supply for AI cluster networking",
    },
    {
        "id": "ai_networking",
        "name": "AI Networking Hardware",
        "layer": "Connectivity",
        "tickers": ["ANET", "CSCO", "CRDO", "CIEN", "NOK"],
        "thesis": "Ethernet switches, SerDes, and optical systems for GPU-to-GPU bandwidth",
    },

    # ── Layer 4: Platform ─────────────────────────────────────────────────────
    {
        "id": "hyperscalers",
        "name": "Hyperscalers",
        "layer": "Platform",
        "tickers": ["MSFT", "GOOGL", "META", "AMZN"],
        "thesis": "Cloud AI workloads, model training at scale, AI-as-a-service distribution",
    },
    {
        "id": "ai_data_platforms",
        "name": "AI Data Platforms",
        "layer": "Platform",
        "tickers": ["SNOW", "MDB", "DDOG", "ESTC", "DT"],
        "thesis": "Data infrastructure and observability budget inside enterprise AI teams",
    },
    {
        "id": "quantum",
        "name": "Quantum Computing",
        "layer": "Platform",
        "tickers": ["IONQ", "RGTI", "QUBT"],
        "thesis": "Next-generation compute paradigm; government and enterprise quantum contracts",
    },

    # ── Layer 5: Applications ─────────────────────────────────────────────────
    {
        "id": "ai_defense",
        "name": "AI Defense & Government",
        "layer": "Applications",
        "tickers": ["PLTR", "BAH", "LDOS", "SAIC", "CACI", "BBAI"],
        "thesis": "Government and DoD AI contracts; defense intelligence and mission systems",
    },
    {
        "id": "enterprise_ai",
        "name": "Enterprise AI",
        "layer": "Applications",
        "tickers": ["CRM", "NOW", "WDAY", "ADBE", "INTU", "ORCL", "SAP"],
        "thesis": "Incumbent SaaS embedding AI into enterprise workflows; same CFO/CIO budget",
    },
    {
        "id": "cybersecurity_ai",
        "name": "Cybersecurity AI",
        "layer": "Applications",
        "tickers": ["CRWD", "PANW", "S", "FTNT", "ZS", "NET", "OKTA"],
        "thesis": "AI-driven endpoint, network, SASE, and identity security platforms",
    },
    {
        "id": "robotics",
        "name": "Robotics & Physical AI",
        "layer": "Applications",
        "tickers": ["ISRG", "TER", "ABBNY", "ROK", "FANUY", "CGNX", "TSLA"],
        "thesis": "Embodied AI; industrial/surgical robots, machine vision, autonomous systems",
    },
]

LAYERS = ["Silicon", "Infrastructure", "Connectivity", "Platform", "Applications"]

# Convenience lookups
THEME_BY_ID = {t["id"]: t for t in THEMES}
THEMES_BY_LAYER = {
    layer: [t for t in THEMES if t["layer"] == layer]
    for layer in LAYERS
}
