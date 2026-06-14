"""
Historical events timeline for Retro Alpha (1994-2004).
Real events with realistic asset impacts. Used as the backbone of the
news system so the game always has meaningful, historically-accurate
headlines even when the LLM is unavailable.
"""

from typing import Dict, List


# Impact magnitudes are calibrated for the simulation (per-month).
# Each event impacts multiple assets; "duration_months" controls how long.
EVENTS: List[Dict] = [
    # 1994
    {
        "year": 1994, "month": 5,
        "headline": "RBI hikes repo rate 50bps to fight inflation",
        "regime": "rate_hike",
        "impact": {"fd": 0.01, "gov_bonds": -0.02, "nifty_50": -0.03, "nifty_it": -0.05,
                   "real_estate": -0.02, "crypto": 0.0, "gold": -0.01, "cash": 0.0},
        "duration_months": 2,
    },
    {
        "year": 1994, "month": 9,
        "headline": "SEBI cracks down on broker cartel; trading volumes surge",
        "regime": "bull_market",
        "impact": {"nifty_50": 0.04, "nifty_it": 0.06, "fd": 0.0, "gov_bonds": 0.01,
                   "real_estate": 0.0, "crypto": 0.0, "gold": 0.0, "cash": 0.0},
        "duration_months": 2,
    },
    # 1995
    {
        "year": 1995, "month": 3,
        "headline": "Mexican peso crisis spooks emerging markets",
        "regime": "fii_exit",
        "impact": {"nifty_50": -0.05, "nifty_it": -0.07, "real_estate": -0.02,
                   "fd": 0.005, "gov_bonds": 0.01, "crypto": 0.0, "gold": 0.02, "cash": 0.0},
        "duration_months": 2,
    },
    {
        "year": 1995, "month": 8,
        "headline": "Monsoon revival boosts rural demand; FMCG rallies",
        "regime": "monsoon_shock",
        "impact": {"nifty_50": 0.03, "real_estate": 0.02, "gold": -0.01,
                   "fd": 0.0, "gov_bonds": 0.0, "nifty_it": 0.02,
                   "crypto": 0.0, "cash": 0.0},
        "duration_months": 2,
    },
    # 1996
    {
        "year": 1996, "month": 5,
        "headline": "United Front govt formed; policy continuity expected",
        "regime": "election_year",
        "impact": {"nifty_50": 0.02, "nifty_it": 0.04, "fd": 0.0, "gov_bonds": 0.005,
                   "real_estate": 0.01, "crypto": 0.0, "gold": 0.0, "cash": 0.0},
        "duration_months": 3,
    },
    # 1997
    {
        "year": 1997, "month": 5,
        "headline": "Thai baht devaluation triggers Asian financial crisis",
        "regime": "market_crash",
        "impact": {"nifty_50": -0.08, "nifty_it": -0.12, "real_estate": -0.05,
                   "fd": 0.005, "gov_bonds": 0.01, "crypto": 0.0, "gold": 0.03, "cash": 0.0},
        "duration_months": 4,
    },
    {
        "year": 1997, "month": 11,
        "headline": "Sukh Ram scandal rocks telecom sector",
        "regime": "bear_market",
        "impact": {"nifty_50": -0.04, "nifty_it": -0.06, "real_estate": -0.01,
                   "fd": 0.0, "gov_bonds": 0.005, "crypto": 0.0, "gold": 0.01, "cash": 0.0},
        "duration_months": 2,
    },
    # 1998
    {
        "year": 1998, "month": 5,
        "headline": "Pokhran-II nuclear tests; sanctions loom",
        "regime": "fii_exit",
        "impact": {"nifty_50": -0.10, "nifty_it": -0.14, "real_estate": -0.04,
                   "fd": 0.01, "gov_bonds": 0.015, "crypto": 0.0, "gold": 0.04, "cash": 0.0},
        "duration_months": 3,
    },
    {
        "year": 1998, "month": 8,
        "headline": "RBI opens asset reconstruction route; recovery rally begins",
        "regime": "recovery",
        "impact": {"nifty_50": 0.06, "nifty_it": 0.10, "real_estate": 0.03,
                   "fd": 0.0, "gov_bonds": 0.005, "crypto": 0.0, "gold": -0.01, "cash": 0.0},
        "duration_months": 3,
    },
    # 1999
    {
        "year": 1999, "month": 5,
        "headline": "Kargil conflict; oil prices spike 30%",
        "regime": "high_inflation",
        "impact": {"nifty_50": -0.05, "nifty_it": -0.08, "real_estate": -0.02,
                   "fd": 0.005, "gov_bonds": -0.01, "crypto": 0.0, "gold": 0.03, "cash": 0.0},
        "duration_months": 2,
    },
    {
        "year": 1999, "month": 10,
        "headline": "Y2K fears and IT boom; Nasdaq crosses 3000",
        "regime": "tech_boom",
        "impact": {"nifty_50": 0.04, "nifty_it": 0.15, "real_estate": 0.02,
                   "fd": 0.0, "gov_bonds": -0.005, "crypto": 0.0, "gold": 0.0, "cash": 0.0},
        "duration_months": 4,
    },
    # 2000
    {
        "year": 2000, "month": 3,
        "headline": "Dot-com bubble bursts; Nasdaq -78% from peak",
        "regime": "market_crash",
        "impact": {"nifty_50": -0.12, "nifty_it": -0.25, "real_estate": -0.04,
                   "fd": 0.01, "gov_bonds": 0.02, "crypto": 0.0, "gold": 0.05, "cash": 0.0},
        "duration_months": 6,
    },
    {
        "year": 2000, "month": 9,
        "headline": "Oil crosses $35/bbl on OPEC supply cuts",
        "regime": "high_inflation",
        "impact": {"nifty_50": -0.03, "nifty_it": -0.05, "real_estate": -0.02,
                   "fd": 0.005, "gov_bonds": -0.01, "crypto": 0.0, "gold": 0.02, "cash": 0.0},
        "duration_months": 2,
    },
    # 2001
    {
        "year": 2001, "month": 1,
        "headline": "Gujarat earthquake; insurance sector hammered",
        "regime": "monsoon_shock",
        "impact": {"nifty_50": -0.04, "nifty_it": -0.05, "real_estate": -0.01,
                   "fd": 0.005, "gov_bonds": 0.01, "crypto": 0.0, "gold": 0.01, "cash": 0.0},
        "duration_months": 2,
    },
    {
        "year": 2001, "month": 9,
        "headline": "9/11 attacks; global markets halt trading",
        "regime": "market_crash",
        "impact": {"nifty_50": -0.10, "nifty_it": -0.15, "real_estate": -0.05,
                   "fd": 0.01, "gov_bonds": 0.02, "crypto": 0.0, "gold": 0.06, "cash": 0.0},
        "duration_months": 3,
    },
    {
        "year": 2001, "month": 12,
        "headline": "Enron collapse exposes audit fraud globally",
        "regime": "bear_market",
        "impact": {"nifty_50": -0.03, "nifty_it": -0.05, "real_estate": 0.0,
                   "fd": 0.005, "gov_bonds": 0.01, "crypto": 0.0, "gold": 0.01, "cash": 0.0},
        "duration_months": 2,
    },
    # 2002
    {
        "year": 2002, "month": 4,
        "headline": "India IT outsourcing boom; TCS, Infosys hit all-time highs",
        "regime": "tech_boom",
        "impact": {"nifty_50": 0.05, "nifty_it": 0.12, "real_estate": 0.02,
                   "fd": 0.0, "gov_bonds": 0.0, "crypto": 0.0, "gold": 0.0, "cash": 0.0},
        "duration_months": 4,
    },
    {
        "year": 2002, "month": 8,
        "headline": "Drought fears; monsoon deficit at 19%",
        "regime": "monsoon_shock",
        "impact": {"nifty_50": -0.03, "nifty_it": -0.02, "real_estate": -0.02,
                   "fd": 0.0, "gov_bonds": 0.005, "crypto": 0.0, "gold": 0.02, "cash": 0.0},
        "duration_months": 2,
    },
    # 2003
    {
        "year": 2003, "month": 3,
        "headline": "Iraq war begins; oil spikes to $40 then retraces",
        "regime": "high_inflation",
        "impact": {"nifty_50": -0.04, "nifty_it": -0.03, "real_estate": -0.01,
                   "fd": 0.005, "gov_bonds": 0.0, "crypto": 0.0, "gold": 0.03, "cash": 0.0},
        "duration_months": 2,
    },
    {
        "year": 2003, "month": 8,
        "headline": "India GDP grows 8.4%; foreign capital floods in",
        "regime": "bull_market",
        "impact": {"nifty_50": 0.07, "nifty_it": 0.10, "real_estate": 0.04,
                   "fd": 0.005, "gov_bonds": 0.0, "crypto": 0.0, "gold": 0.0, "cash": 0.0},
        "duration_months": 4,
    },
    # 2004
    {
        "year": 2004, "month": 2,
        "headline": "BJP loses election; Congress-led UPA forms govt",
        "regime": "election_year",
        "impact": {"nifty_50": -0.04, "nifty_it": -0.02, "real_estate": 0.0,
                   "fd": 0.0, "gov_bonds": 0.005, "crypto": 0.0, "gold": 0.0, "cash": 0.0},
        "duration_months": 2,
    },
]


def event_for_month(year: int, month: int) -> Dict:
    """Return the historical event for the given month, or a generic
    background-noise event so the game always has something to report."""
    for ev in EVENTS:
        if ev["year"] == year and ev["month"] == month:
            return ev
    return {
        "year": year,
        "month": month,
        "headline": f"Markets trade in tight range; low volatility session",
        "regime": "stagnation",
        "impact": {a: 0.0 for a in [
            "cash", "fd", "gov_bonds", "nifty_50", "nifty_it",
            "real_estate", "crypto", "gold"
        ]},
        "duration_months": 1,
    }


def next_upcoming_event(year: int, month: int) -> Dict:
    """Return the next historical event strictly after the given date."""
    flat = (year, month)
    for ev in EVENTS:
        if (ev["year"], ev["month"]) > flat:
            return ev
    return EVENTS[-1]
