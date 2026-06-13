"""Append extra mentor rows to clean dataset and re-validate."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN_FILE = ROOT / "data" / "retro-alpha-clean.jsonl"
EXTRA_FILE = ROOT / "data" / "retro-alpha-mentor-extra.jsonl"
FINAL_FILE = ROOT / "data" / "retro-alpha-final.jsonl"


def parse_mentor(response: str) -> dict | None:
    try:
        roast = re.search(r"roast:\s*(.+)", response).group(1).strip()
        sharpe = float(re.search(r"sharpe_ratio:\s*([-\d.]+)", response).group(1))
        lesson = re.search(r"lesson:\s*(.+)", response).group(1).strip()
        suggestion = re.search(r"suggestion:\s*(.+)", response).group(1).strip()
        return {"roast": roast, "sharpe_ratio": sharpe, "lesson": lesson, "suggestion": suggestion}
    except Exception:
        return None


def main():
    if not CLEAN_FILE.exists():
        print(f"Clean file not found: {CLEAN_FILE}")
        sys.exit(1)
    if not EXTRA_FILE.exists():
        print(f"Extra file not found: {EXTRA_FILE}")
        sys.exit(1)

    # Copy clean file
    with open(CLEAN_FILE, "r", encoding="utf-8") as f:
        clean_rows = [line for line in f if line.strip()]

    # Parse and append extra mentor rows
    extra_valid = 0
    extra_invalid = 0
    with open(EXTRA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if parse_mentor(row.get("response", "")):
                clean_rows.append(line)
                extra_valid += 1
            else:
                extra_invalid += 1

    with open(FINAL_FILE, "w", encoding="utf-8") as f:
        for line in clean_rows:
            f.write(line + "\n")

    print(f"Extra mentor valid: {extra_valid}, invalid: {extra_invalid}")
    print(f"Final dataset: {FINAL_FILE} ({len(clean_rows)} rows)")


if __name__ == "__main__":
    main()
