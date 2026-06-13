"""
Mini audit test: generate a small batch of each task type and validate
the structured text responses can be parsed.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

from generate_dataset import generate_prompts, generate_wave, OUTPUT_FILE


def to_decimal(value_str: str) -> float:
    value_str = value_str.strip()
    if value_str.endswith("%"):
        return float(value_str[:-1]) / 100.0
    return float(value_str)


def parse_agent(response: str) -> dict:
    response = response.strip()
    if not response:
        raise ValueError("empty response")
    agent = re.search(r"agent:\s*(\w+)", response).group(1)
    action_match = re.search(r"action:\s*(buy|sell|hold)\s+(\w+)\s+([\d.%]+)", response)
    reason = re.search(r"reason:\s*(.+)", response).group(1).strip()
    sentiment = re.search(r"sentiment:\s*(\w+)", response).group(1)
    return {
        "agent": agent,
        "actions": [{"asset": action_match.group(2), "action": action_match.group(1), "amount_pct": to_decimal(action_match.group(3)), "reason": reason}],
        "sentiment": sentiment
    }


def parse_news(response: str) -> dict:
    response = response.strip()
    if not response:
        raise ValueError("empty response")
    headline = re.search(r"headline:\s*(.+)", response).group(1).strip()
    impact_match = re.search(r"impact:\s*(.+?)(?:\nduration:|$)", response, re.DOTALL)
    duration = int(re.search(r"duration:\s*(\d+)", response).group(1))
    impact = {}
    for token in impact_match.group(1).strip().split():
        if ":" in token:
            k, v = token.split(":")
            impact[k] = to_decimal(v)
    return {"headline": headline, "impact": impact, "duration_months": duration}


def parse_mentor(response: str) -> dict:
    response = response.strip()
    if not response:
        raise ValueError("empty response")
    roast = re.search(r"roast:\s*(.+)", response).group(1).strip()
    sharpe = float(re.search(r"sharpe_ratio:\s*([-\d.]+)", response).group(1))
    lesson = re.search(r"lesson:\s*(.+)", response).group(1).strip()
    suggestion = re.search(r"suggestion:\s*(.+)", response).group(1).strip()
    return {"roast": roast, "sharpe_ratio": sharpe, "lesson": lesson, "suggestion": suggestion}


def parse_guardrail(response: str) -> dict:
    response = response.strip()
    if not response:
        raise ValueError("empty response")
    return {"error": re.search(r"error:\s*(.+)", response).group(1).strip()}


PARSERS = {
    "agent_decision": parse_agent,
    "news_impact": parse_news,
    "sharpe_mentor": parse_mentor,
    "guardrail": parse_guardrail,
}


async def main():
    test_file = OUTPUT_FILE.with_name("retro-alpha-test.jsonl")
    if test_file.exists():
        test_file.unlink()

    waves = [
        ("agent", 5),
        ("news", 5),
        ("mentor", 5),
        ("guardrail", 5),
    ]

    all_rows = []
    for task, count in waves:
        print(f"Testing {task} with {count} rows...")
        prompts = generate_prompts(task, count)
        results = await generate_wave(prompts, f"test-{task}")
        print(f"  Got {len(results)}/{count} non-empty rows")
        all_rows.extend(results)

    with open(test_file, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nTest output: {test_file}")
    print(f"Total test rows: {len(all_rows)}")

    parse_ok = 0
    parse_fail = 0
    for row in all_rows:
        parser = PARSERS[row["task"]]
        try:
            parser(row["response"])
            parse_ok += 1
        except Exception as e:
            parse_fail += 1
            print(f"Parse fail ({row['task']}): {e}")
            print(f"  Response: {repr(row['response'][:200])}")

    print(f"Parsed successfully: {parse_ok}/{len(all_rows)}")
    if parse_fail > 0:
        print("TEST FAILED")
        return 1

    print("TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
