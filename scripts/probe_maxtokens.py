"""Probe MiniMax-M3 max_tokens behavior."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("ZENMUX_API_KEY")
BASE_URL = os.getenv("BASE_URL") or os.getenv("ZENMUX_BASE_URL")
MODEL = os.getenv("MODEL") or os.getenv("ZENMUX_MODEL")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

for max_tokens in [100, 300, 600, 1200, 2000]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Output JSON only."},
            {"role": "user", "content": "List numbers 1 to 100 as a JSON array under key 'numbers'. Compact single line."}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }
    print(f"\n=== max_tokens={max_tokens} ===")
    try:
        resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        print(f"Completion tokens: {usage.get('completion_tokens')}")
        print(f"Content length: {len(content)}")
        print(content[:200])
    except Exception as e:
        print(f"Error: {e}")
