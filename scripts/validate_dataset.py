"""
Validate the generated text-format dataset, filter parseable rows,
and write a clean dataset ready for fine-tuning.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "data" / "retro-alpha-training-v1.jsonl"
CLEAN_FILE = ROOT / "data" / "retro-alpha-clean.jsonl"


def to_decimal(value_str: str) -> float:
    value_str = value_str.strip()
    if value_str.endswith("%"):
        return float(value_str[:-1]) / 100.0
    return float(value_str)


def parse_agent(response: str) -> dict | None:
    try:
        agent = re.search(r"agent:\s*<?(\w+)>?", response).group(1).lower()
        action_match = re.search(r"action:\s*(buy|sell|hold)\s+(\w+)\s+([\d.%]+)", response)
        reason = re.search(r"reason:\s*(.+)", response).group(1).strip()
        sentiment = re.search(r"sentiment:\s*<?(\w+)>?", response).group(1).lower()
        return {
            "agent": agent,
            "actions": [{"asset": action_match.group(2), "action": action_match.group(1), "amount_pct": to_decimal(action_match.group(3)), "reason": reason}],
            "sentiment": sentiment
        }
    except Exception:
        return None


def parse_news(response: str) -> dict | None:
    try:
        headline = re.search(r"headline:\s*(.+)", response).group(1).strip()
        impact_match = re.search(r"impact:\s*(.+?)(?:\nduration:|$)", response, re.DOTALL)
        duration = int(re.search(r"duration:\s*(\d+)", response).group(1))
        impact = {}
        for token in impact_match.group(1).strip().split():
            if ":" in token:
                k, v = token.split(":")
                impact[k] = to_decimal(v)
        required = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"]
        if not all(k in impact for k in required):
            return None
        return {"headline": headline, "impact": impact, "duration_months": duration}
    except Exception:
        return None


def parse_mentor(response: str) -> dict | None:
    try:
        roast = re.search(r"roast:\s*(.+)", response).group(1).strip()
        sharpe = float(re.search(r"sharpe_ratio:\s*([-\d.]+)", response).group(1))
        lesson = re.search(r"lesson:\s*(.+)", response).group(1).strip()
        suggestion = re.search(r"suggestion:\s*(.+)", response).group(1).strip()
        return {"roast": roast, "sharpe_ratio": sharpe, "lesson": lesson, "suggestion": suggestion}
    except Exception:
        return None


def parse_guardrail(response: str) -> dict | None:
    try:
        return {"error": re.search(r"error:\s*(.+)", response).group(1).strip()}
    except Exception:
        return None


PARSERS = {
    "agent_decision": parse_agent,
    "news_impact": parse_news,
    "sharpe_mentor": parse_mentor,
    "guardrail": parse_guardrail,
}


def validate():
    if not INPUT_FILE.exists():
        print(f"Dataset not found: {INPUT_FILE}")
        sys.exit(1)

    total = 0
    valid = 0
    errors = 0
    empty = 0
    task_counts = Counter()
    valid_task_counts = Counter()

    with open(INPUT_FILE, "r", encoding="utf-8") as f_in, open(CLEAN_FILE, "w", encoding="utf-8") as f_out:
        for line_num, line in enumerate(f_in, 1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Line {line_num}: JSON parse error: {e}")
                errors += 1
                continue

            task = row.get("task")
            task_counts[task] += 1
            response = row.get("response", "").strip()
            if not response:
                empty += 1
                continue

            parser = PARSERS.get(task)
            if not parser:
                print(f"Line {line_num}: unknown task '{task}'")
                errors += 1
                continue

            parsed = parser(response)
            if parsed is None:
                errors += 1
                if errors <= 20:
                    print(f"Line {line_num} ({task}): parse error")
                    print(f"  Response: {repr(response[:200])}")
                continue

            valid += 1
            valid_task_counts[task] += 1
            f_out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\n=== Validation Report ===")
    print(f"Total rows: {total}")
    print(f"Valid rows: {valid}")
    print(f"Invalid/empty rows: {errors + empty}")
    print(f"Empty responses: {empty}")
    print("Task distribution (input):")
    for task, count in task_counts.most_common():
        print(f"  {task}: {count}")
    print("Valid task distribution:")
    for task, count in valid_task_counts.most_common():
        print(f"  {task}: {count}")
    print(f"\nClean dataset: {CLEAN_FILE}")

    if valid >= 1500:
        print(f"\nDataset is usable for fine-tuning ({valid} valid rows).")
        return 0
    else:
        print(f"\nOnly {valid} valid rows. Consider generating more.")
        return 1


if __name__ == "__main__":
    sys.exit(validate())
