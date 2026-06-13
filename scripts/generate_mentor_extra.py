"""Generate extra mentor rows to supplement the clean dataset."""

import asyncio
import json
import os
import random
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("ZENMUX_API_KEY")
BASE_URL = os.getenv("BASE_URL") or os.getenv("ZENMUX_BASE_URL", "https://api.tokenrouter.com/v1")
MODEL = os.getenv("MODEL") or os.getenv("ZENMUX_MODEL", "MiniMax-M3")

ROOT = Path(__file__).resolve().parent.parent
CLEAN_FILE = ROOT / "data" / "retro-alpha-clean.jsonl"
EXTRA_FILE = ROOT / "data" / "retro-alpha-mentor-extra.jsonl"

ASSETS = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"]
STYLES = ["savage", "educational", "sarcastic", "encouraging"]

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def random_portfolio() -> dict:
    weights = [random.random() for _ in ASSETS]
    total = sum(weights)
    return {a: round(w / total, 3) for a, w in zip(ASSETS, weights)}


def build_prompt(style: str) -> dict:
    allocations = random_portfolio()
    if random.random() < 0.6:
        heavy = random.choice(["crypto", "nifty_it", "real_estate"])
        allocations = {a: 0.05 for a in ASSETS}
        allocations[heavy] = 0.65
    start = random.choice([500000, 1000000, 2000000, 5000000])
    drawdown = round(random.uniform(-0.05, -0.45), 2)
    end = int(start * (1 + drawdown))
    sharpe = round(random.uniform(-1.2, 1.5), 2)

    system = "You are a finance professor NPC in a video game. Output a year-end review in this exact short format:\nroast: <roast, max 50 chars>\nsharpe_ratio: <number>\nlesson: <lesson, max 80 chars>\nsuggestion: <tip, max 50 chars>"

    user = f"""Example:
roast: 65% crypto? Portfolio vanished.
sharpe_ratio: -0.5
lesson: Sharpe measures return per unit risk.
suggestion: Cap crypto at 10%.

Now generate for: start=₹{start/100000:.1f}L, end=₹{end/100000:.1f}L, drawdown={drawdown*100:.0f}%, sharpe={sharpe}, style={style}"""

    return {"system": system, "user": user, "task": "sharpe_mentor", "style": style}


def clean(text: str) -> str:
    text = text.strip()
    while "<think>" in text and "</think>" in text:
        s = text.find("<think>")
        e = text.find("</think>") + len("</think>")
        text = text[:s] + text[e:]
    return text.strip()


async def call_one(session, prompt, semaphore):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    for attempt in range(5):
        async with semaphore:
            try:
                async with session.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60) as resp:
                    data = await resp.json()
                    content = data["choices"][0]["message"].get("content", "")
                    if content.strip():
                        return {
                            "task": prompt["task"],
                            "system": prompt["system"],
                            "user": prompt["user"],
                            "response": clean(content),
                            "metadata": {"style": prompt["style"]}
                        }
            except Exception:
                await asyncio.sleep(0.5)
    return None


async def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    semaphore = asyncio.Semaphore(10)
    prompts = [build_prompt(random.choice(STYLES)) for _ in range(count)]

    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [call_one(session, p, semaphore) for p in prompts]
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            if result:
                results.append(result)
            if (i + 1) % 50 == 0 or (i + 1) == len(tasks):
                print(f"[{i+1}/{len(tasks)}] valid: {len(results)}")

    with open(EXTRA_FILE, "w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Generated {len(results)} extra mentor rows -> {EXTRA_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
