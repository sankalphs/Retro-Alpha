"""Upload the final clean dataset to Hugging Face."""

import os
import sys
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
FINAL_FILE = ROOT / "data" / "retro-alpha-final.jsonl"
REPO_ID = "build-small-hackathon/retro-alpha-dataset"


def main():
    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN not found in .env")
        sys.exit(1)

    if not FINAL_FILE.exists():
        print(f"Final dataset not found: {FINAL_FILE}")
        sys.exit(1)

    print(f"Loading dataset from {FINAL_FILE}...")
    with open(FINAL_FILE, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(rows)} rows")

    # Build chat-format conversations for fine-tuning
    def build_conversation(row):
        return {
            "messages": [
                {"role": "system", "content": row["system"]},
                {"role": "user", "content": row["user"]},
                {"role": "assistant", "content": row["response"]},
            ],
            "task": row["task"],
            "metadata": row.get("metadata", {}),
        }

    dataset = Dataset.from_list([build_conversation(r) for r in rows])

    print(f"Pushing to {REPO_ID}...")
    dataset.push_to_hub(REPO_ID, token=token, private=False)
    print("Done.")


if __name__ == "__main__":
    import json  # noqa: F401
    main()
