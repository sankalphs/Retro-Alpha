"""Test MiniMax-M3 with concurrency=1 and delays."""

import asyncio
import json
import os
import time

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("ZENMUX_API_KEY")
BASE_URL = os.getenv("BASE_URL") or os.getenv("ZENMUX_BASE_URL")
MODEL = os.getenv("MODEL") or os.getenv("ZENMUX_MODEL")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

prompts = [
    {"system": "You are an NPC behavior designer for a fictional Indian stock-market video game. Output JSON only.", "user": "Whale sees monsoon shock. Output compact JSON: {\"agent\":\"whale\",\"actions\":[{\"asset\":\"gov_bonds\",\"action\":\"buy\",\"amount_pct\":0.15,\"reason\":\"safety\"}],\"sentiment\":\"cautious\"}"},
    {"system": "You are a scenario writer for a fictional Indian stock-market video game. Output JSON only.", "user": "Generate a rate hike headline and impact. Compact JSON: {\"headline\":\"RBI hikes repo rate\",\"impact\":{\"cash\":0,\"fd\":0.1,\"gov_bonds\":-0.05,\"nifty_50\":-0.05,\"nifty_it\":-0.08,\"real_estate\":-0.03,\"crypto\":-0.1,\"gold\":0.02},\"duration_months\":3}"},
]

async def call_one(session, prompt, delay):
    await asyncio.sleep(delay)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    try:
        async with session.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60) as resp:
            data = await resp.json()
            content = data["choices"][0]["message"].get("content", "")
            return content
    except Exception as e:
        return f"ERROR: {e}"

async def main():
    async with aiohttp.ClientSession() as session:
        for i in range(10):
            prompt = prompts[i % 2]
            content = await call_one(session, prompt, 1.0)
            print(f"\n--- Call {i+1} ---")
            print(content[:300])

if __name__ == "__main__":
    asyncio.run(main())
