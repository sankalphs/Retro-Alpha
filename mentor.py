"""Sharpe Ratio Mentor — year-end review generator."""

import re
from typing import Dict

from agents import generate, clean_text, sanitize_for_display


def _deterministic_review(summary: Dict) -> Dict:
    """Build a real, useful mentor review from the numeric summary alone.

    Used when the LLM is unavailable or returns unparseable output, so the
    player always gets an actual roast grounded in their numbers (never a
    raw parse error).
    """
    starting = float(summary.get("starting_value", 1_000_000))
    ending = float(summary.get("ending_value", starting))
    sharpe = float(summary.get("sharpe_ratio", 0.0))
    allocations = summary.get("allocations") or {}
    total_alloc = sum(float(v) for v in allocations.values())

    # Pick a deterministic roast based on performance band
    pct_change = ((ending - starting) / starting * 100.0) if starting else 0.0
    if pct_change >= 100:
        roast = f"You doubled the book. Buffett is taking notes."
    elif pct_change >= 25:
        roast = f"Compounding works. Even your broker is surprised."
    elif pct_change >= 0:
        roast = f"You survived. The market didn't kill you. Yet."
    elif pct_change >= -25:
        roast = f"Pain is tuition. You paid for a semester."
    else:
        roast = f"That wasn't investing. That was a donation."

    # Find the dominant allocation and call it out
    if allocations:
        biggest = max(allocations.items(), key=lambda kv: kv[1])
        asset_name = str(biggest[0]).replace("_", " ")
        share_pct = float(biggest[1]) * 100
        if share_pct >= 70 and asset_name not in ("cash", "fd"):
            lesson = f"{share_pct:.0f}% in {asset_name} is conviction, not a plan."
            suggestion = f"Cap {asset_name} at 40%. Add bonds or gold."
        elif total_alloc < 0.3:
            lesson = "Idle cash lost to inflation this year."
            suggestion = "Move 30% of cash into FD or gov bonds."
        else:
            lesson = "Sharpe ratio measures return per unit of pain."
            suggestion = "Trim the weakest performer and rebalance."
    else:
        lesson = "Sharpe ratio measures return per unit of pain."
        suggestion = "Build a core allocation: 50% Nifty, 20% bonds, 10% gold."

    if sharpe >= 1.0:
        suggestion = "Sharpe > 1: lock in gains, don't get heroic."
    elif sharpe <= 0:
        suggestion = "Negative Sharpe: cut losers, raise cash."

    return {
        "roast": roast[:80],
        "sharpe_ratio": round(sharpe, 2),
        "lesson": lesson[:140],
        "suggestion": suggestion[:80],
    }


def parse_mentor_response(response: str, summary: Dict) -> dict:
    if not response or not response.strip():
        return _deterministic_review(summary)

    text = clean_text(response)
    if not text:
        return _deterministic_review(summary)

    roast = sharpe_s = lesson = suggestion = None
    try:
        m = re.search(r"roast:\s*(.+)", text, re.IGNORECASE)
        if m:
            roast = sanitize_for_display(m.group(1).strip(), 80)
    except Exception:
        pass
    try:
        m = re.search(r"sharpe_ratio:\s*([-\d.]+)", text, re.IGNORECASE)
        if m:
            sharpe_s = float(m.group(1))
    except Exception:
        pass
    try:
        m = re.search(r"lesson:\s*(.+)", text, re.IGNORECASE)
        if m:
            lesson = sanitize_for_display(m.group(1).strip(), 140)
    except Exception:
        pass
    try:
        m = re.search(r"suggestion:\s*(.+)", text, re.IGNORECASE)
        if m:
            suggestion = sanitize_for_display(m.group(1).strip(), 80)
    except Exception:
        pass

    fallback = _deterministic_review(summary)
    return {
        "roast": (roast or fallback["roast"])[:80],
        "sharpe_ratio": sharpe_s if sharpe_s is not None else fallback["sharpe_ratio"],
        "lesson": (lesson or fallback["lesson"])[:140],
        "suggestion": (suggestion or fallback["suggestion"])[:80],
    }


def generate_review(summary: dict) -> dict:
    system = (
        "You are a sarcastic but caring Indian finance professor in a video game. "
        "Output ONLY these 4 lines, nothing else:\n"
        "roast: <witty roast, under 60 chars>\n"
        "sharpe_ratio: <number, e.g. 0.85>\n"
        "lesson: <explain Sharpe ratio simply, under 100 chars>\n"
        "suggestion: <one concrete tip, under 60 chars>\n"
        "No thinking tags, no markdown, no extra text."
    )
    prompt = (
        f"Starting ₹{summary['starting_value']:,.0f}. "
        f"Ending ₹{summary['ending_value']:,.0f}. "
        f"Drawdown {summary['max_drawdown']*100:.0f}%. "
        f"Sharpe {summary['sharpe_ratio']}. "
        f"Top alloc: {max(summary['allocations'].items(), key=lambda kv: kv[1]) if summary['allocations'] else 'cash'}."
    )
    response = generate(prompt, system=system, max_tokens=200, temperature=0.5)
    return parse_mentor_response(response, summary)
