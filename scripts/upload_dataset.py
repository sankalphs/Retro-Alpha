"""Upload the final clean dataset to Hugging Face."""

import json
import os
import sys
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from huggingface_hub import HfApi

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
FINAL_FILE = ROOT / "data" / "retro-alpha-final.jsonl"

# Prefer explicit env vars, then default to build-small-hackathon namespace.
HF_USER = os.getenv("HF_USER", "build-small-hackathon")
REPO_ID = os.getenv("DATASET_REPO", f"{HF_USER}/retro-alpha-dataset")


def main():
    token = os.getenv("HF_TOKEN")
    if not token:
        print("HF_TOKEN not found in .env or environment")
        sys.exit(1)

    if not FINAL_FILE.exists():
        print(f"Final dataset not found: {FINAL_FILE}")
        sys.exit(1)

    print(f"Loading dataset from {FINAL_FILE}...")
    with open(FINAL_FILE, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(rows)} rows")

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

    api = HfApi(token=token)
    try:
        api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True)
    except Exception as e:
        print(f"Could not create/find dataset repo {REPO_ID}: {e}")
        # Fallback to user namespace if org namespace fails.
        me = api.whoami()["name"]
        fallback = f"{me}/retro-alpha-dataset"
        if fallback != REPO_ID:
            print(f"Trying fallback repo: {fallback}")
            api.create_repo(repo_id=fallback, repo_type="dataset", exist_ok=True)
            dataset.push_to_hub(fallback, token=token, private=False)
            print(f"Pushed to fallback {fallback}")
            return
        raise

    print(f"Pushing to {REPO_ID}...")
    dataset.push_to_hub(REPO_ID, token=token, private=False)
    print("Done.")


if __name__ == "__main__":
    main()
