"""Test MiniMax-M3 with simple text format instead of JSON."""

import asyncio
import os
import random

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

REGIMES = ["bull_market", "bear_market", "market_crash", "recovery", "high_inflation", "rate_hike", "rate_cut"]
PERSONAS = ["whale", "retail", "permabull"]
ASSETS = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"]

def clean(text):
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
        "max_tokens": 400
    }
    for attempt in range(5):
        async with semaphore:
            try:
                async with session.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60) as resp:
                    data = await resp.json()
                    content = data["choices"][0]["message"].get("content", "")
                    cleaned = clean(content)
                    # Check it has required fields
                    return cleaned
            except Exception:
                await asyncio.sleep(0.5)
    return ""

async def main():
    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as session:
        # Test agent simple text
        print("=== Agent simple text ===")
        for _ in range(5):
            persona = random.choice(PERSONAS)
            regime = random.choice(REGIMES)
            system = "You are an NPC behavior designer. Output only the decision in this exact format: agent: <persona>\naction: <buy|sell|hold> <asset> <amount_pct>\nreason: <short reason>\nsentiment: <bullish|bearish|neutral|panic|cautious>"
            user = f"Market regime: {regime}. Persona: {persona}. Available assets: {ASSETS}."
            content = await call_one(session, {"system": system, "user": user}, semaphore)
            print(content)
            print("---")

        # Test news simple text
        print("\n=== News simple text ===")
        for _ in range(3):
            regime = random.choice(REGIMES)
            system = "You are a scenario writer. Output only in this exact format:\nheadline: <short headline>\nimpact: cash:<n> fd:<n> bonds:<n> nifty:<n> it:<n> realestate:<n> crypto:<n> gold:<n>\nduration: <months>"
            user = f"Generate an Indian financial headline for regime: {regime}"
            content = await call_one(session, {"system": system, "user": user}, semaphore)
            print(content)
            print("---")

if __name__ == "__main__":
    asyncio.run(main())
