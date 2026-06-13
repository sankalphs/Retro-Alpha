"""Sharpe Ratio Mentor — year-end review generator."""

import json
import re

from agents import generate


def parse_mentor_response(response: str) -> dict:
    response = response.strip()
    try:
        roast = re.search(r"roast:\s*(.+)", response).group(1).strip()
        sharpe = float(re.search(r"sharpe_ratio:\s*([-\d.]+)", response).group(1))
        lesson = re.search(r"lesson:\s*(.+)", response).group(1).strip()
        suggestion = re.search(r"suggestion:\s*(.+)", response).group(1).strip()
        return {"roast": roast, "sharpe_ratio": sharpe, "lesson": lesson, "suggestion": suggestion}
    except Exception as e:
        return {
            "roast": "Could not parse review.",
            "sharpe_ratio": 0.0,
            "lesson": f"Parse error: {e}",
            "suggestion": "Try again next year.",
        }


def generate_review(summary: dict) -> dict:
    system = "You are a sarcastic but caring Indian finance professor in a video game. Output a year-end review in exact format:\nroast: <witty roast, under 60 chars>\nsharpe_ratio: <number>\nlesson: <explain Sharpe ratio simply, under 100 chars>\nsuggestion: <one concrete tip, under 60 chars>"
    prompt = (
        f"Starting value: ₹{summary['starting_value']:,}. "
        f"Ending value: ₹{summary['ending_value']:,.0f}. "
        f"Max drawdown: {summary['max_drawdown']*100:.0f}%. "
        f"Allocation: {json.dumps(summary['allocations'])}. "
        f"Sharpe ratio: {summary['sharpe_ratio']}."
    )
    response = generate(prompt, system=system, max_tokens=250)
    return parse_mentor_response(response)
