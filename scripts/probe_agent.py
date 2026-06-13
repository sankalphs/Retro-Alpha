"""Probe a single agent decision to debug empty/truncated responses."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ZENMUX_API_KEY")
BASE_URL = os.getenv("ZENMUX_BASE_URL")
MODEL = os.getenv("ZENMUX_MODEL")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

system = "You are the Institutional Whale: slow, disciplined, focused on G-Secs, Nifty 50, and gold. You hate panic and chase safety."
user = """Current market regime: Monsoon Shock.
Latest headline: Deficient monsoon threatens rural demand.
Asset prices (normalized): {"cash": 0.947, "fd": 1.173, "gov_bonds": 1.196, "nifty_50": 0.902, "nifty_it": 1.128, "real_estate": 1.176, "crypto": 0.971, "gold": 0.925}.
Your current portfolio allocation: {"cash": 0.085, "fd": 0.135, "gov_bonds": 0.188, "nifty_50": 0.092, "nifty_it": 0.021, "real_estate": 0.19, "crypto": 0.095, "gold": 0.195}.

Decide what to do. Output strictly JSON matching this schema:
{
  "agent": "whale",
  "actions": [
    {"asset": "<asset id>", "action": "buy|sell|hold", "amount_pct": 0.0-1.0, "reason": "short reason"}
  ],
  "sentiment": "bullish|bearish|neutral|panic|cautious"
}

Be true to your persona."""

for max_tokens in [400, 800, 1200]:
    for use_response_format in [True, False]:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        if use_response_format:
            payload["response_format"] = {"type": "json_object"}

        print(f"\n=== max_tokens={max_tokens}, response_format={use_response_format} ===")
        try:
            resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"Content length: {len(content)}")
            print(content[:500])
        except Exception as e:
            print(f"Error: {e}")
