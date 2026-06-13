"""Test MiniMax-M3 success rate on a larger batch."""

import asyncio
import json
import os
import random
import time

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("ZENMUX_API_KEY")
BASE_URL = os.getenv("BASE_URL") or os.getenv("ZENMUX_BASE_URL")
MODEL = os.getenv("MODEL") or os.getenv("ZENMUX_MODEL")

ASSETS = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"]
REGIMES = ["bull_market", "bear_market", "market_crash", "recovery", "high_inflation", "rate_hike", "rate_cut"]
PERSONAS = {
    "whale": "Institutional Whale: slow, disciplined, bonds + Nifty 50",
    "retail": "Retail Day Trader: panic sells, FOMOs hype",
    "permabull": "Tech Permabull: IT and crypto only go up"
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def clean(text):
    text = text.strip()
    while "<think>" in text and "</think>" in text:
        s = text.find("<think>")
        e = text.find("</think>") + len("</think>")
        text = text[:s] + text[e:]
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    text = text.strip()
    if not text.startswith("{"):
        s = text.find("{")
        if s != -1: text = text[s:]
    if not text.endswith("}"):
        e = text.rfind("}")
        if e != -1: text = text[:e+1]
    return text

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
                    if resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    resp.raise_for_status()
                    data = await resp.json()
                    if not data.get("choices"):
                        raise ValueError("no choices")
                    content = data["choices"][0]["message"].get("content", "")
                    if not content.strip():
                        raise ValueError("empty")
                    cleaned = clean(content)
                    json.loads(cleaned)
                    return True
            except Exception:
                await asyncio.sleep(0.5)
    return False

async def main():
    prompts = []
    for _ in range(50):
        persona = random.choice(list(PERSONAS.keys()))
        regime = random.choice(REGIMES)
        system = f"You are an NPC behavior designer. Write a {PERSONAS[persona]} decision as compact JSON only."
        user = f'Return compact JSON: {{"agent":"{persona}","actions":[{{"asset":"nifty_it","action":"buy","amount_pct":0.15,"reason":"under 10 words"}}],"sentiment":"bullish"}}'
        prompts.append({"system": system, "user": user})

    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as session:
        tasks = [call_one(session, p, semaphore) for p in prompts]
        results = await asyncio.gather(*tasks)

    success = sum(results)
    print(f"Success rate: {success}/{len(results)} = {success/len(results)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
