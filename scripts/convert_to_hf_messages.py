"""Convert Retro Alpha JSONL into Hugging Face messages format."""

import json
from pathlib import Path


def convert(input_path: str, output_path: str, include_reasoning: bool = False):
    """Convert rows into HF chat messages format.

    Each row becomes a dict with a 'messages' list [system, user, assistant].
    If include_reasoning is True, assistant content is wrapped in <think> tags
    to preserve Nemotron 3 reasoning behavior per Unsloth docs.
    """
    in_path = Path(input_path)
    out_path = Path(output_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with in_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            response = row["response"]
            if include_reasoning:
                # Minimal chain-of-thought prefix to keep reasoning habit
                response = f"<think>{row['task']}: analyze inputs, pick best action.</think>\n{response}"
            messages = [
                {"role": "system", "content": row["system"]},
                {"role": "user", "content": row["user"]},
                {"role": "assistant", "content": response},
            ]
            fout.write(json.dumps({"messages": messages, "metadata": row.get("metadata", {})}, ensure_ascii=False) + "\n")
            total += 1
    print(f"Converted {total} rows -> {out_path}")


if __name__ == "__main__":
    convert("data/retro-alpha-final.jsonl", "data/retro-alpha-messages.jsonl", include_reasoning=False)
