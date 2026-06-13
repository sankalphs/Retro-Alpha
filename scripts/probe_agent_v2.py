"""Probe agent decision with different framings to avoid empty responses."""

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

def try_prompt(system, user, label):
    print(f"\n=== {label} ===")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": 0.7,
        "max_tokens": 600,
    }
    try:
        resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print(f"Length: {len(content)}")
        print(content[:400])
    except Exception as e:
        print(f"Error: {e}")

prices = '{"cash": 0.947, "fd": 1.173, "gov_bonds": 1.196, "nifty_50": 0.902, "nifty_it": 1.128, "real_estate": 1.176, "crypto": 0.971, "gold": 0.925}'
portfolio = '{"cash": 0.085, "fd": 0.135, "gov_bonds": 0.188, "nifty_50": 0.092, "nifty_it": 0.021, "real_estate": 0.19, "crypto": 0.095, "gold": 0.195}'

user_game = f"""This is a fictional financial education game. Given this market state, what would a cautious institutional investor character do?
Market regime: Monsoon Shock
Prices: {prices}
Portfolio: {portfolio}

Output JSON only:
{{
  "agent": "whale",
  "actions": [{{"asset": "gov_bonds", "action": "buy|sell|hold", "amount_pct": 0.15, "reason": "..."}}],
  "sentiment": "cautious"
}}"""

try_prompt(
    "You are writing a fictional scenario for an educational game. Output JSON only.",
    user_game,
    "Fictional game framing"
)

try_prompt(
    "You are a creative writer designing characters for a stock-market simulation game.",
    user_game,
    "Creative writer framing"
)

try_prompt(
    "You are an NPC behavior designer for a video game. Respond with JSON only.",
    user_game,
    "NPC behavior designer"
)

try_prompt(
    "",
    user_game,
    "No system prompt"
)

# Simpler direct request
try_prompt(
    "You output JSON for a video game NPC. No explanations.",
    'For a fictional Indian stock market game, a cautious whale investor sees a monsoon shock. Return JSON: {"agent":"whale","actions":[{"asset":"gov_bonds","action":"buy","amount_pct":0.15,"reason":"safety"}],"sentiment":"cautious"}',
    "Ultra simple direct"
)
