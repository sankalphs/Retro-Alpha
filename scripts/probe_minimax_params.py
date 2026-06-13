"""Probe MiniMax-M3 API parameters to disable thinking or increase output."""

import json
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

base_messages = [
    {"role": "system", "content": "You are a JSON API. Output valid JSON only. No explanation, no thinking, no markdown."},
    {"role": "user", "content": 'Return compact JSON: {"agent":"whale","actions":[{"asset":"gov_bonds","action":"buy","amount_pct":0.15,"reason":"safety"}],"sentiment":"cautious"}'}
]

variants = [
    {"max_tokens": 2000},
    {"max_tokens": 4000},
    {"max_tokens": 2000, "temperature": 0.0},
    {"max_tokens": 2000, "response_format": {"type": "json_object"}},
    {"max_tokens": 2000, "extra_body": {"include_thinking": False}},
    {"max_tokens": 2000, "extra_body": {"thinking": False}},
    {"max_tokens": 2000, "extra_body": {"reasoning": False}},
    {"max_tokens": 2000, "extra_body": {"no_thinking": True}},
]

for i, variant in enumerate(variants):
    print(f"\n=== Variant {i+1}: {variant} ===")
    payload = {
        "model": MODEL,
        "messages": base_messages,
    }
    # extra_body is a client-side concept; for raw requests, merge top-level keys
    extra = variant.pop("extra_body", {})
    payload.update(variant)
    payload.update(extra)

    try:
        resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
        data = resp.json()
        content = data["choices"][0]["message"].get("content", "")
        usage = data.get("usage", {})
        print(f"Status: {resp.status_code}, completion_tokens: {usage.get('completion_tokens')}")
        print(content[:400])
    except Exception as e:
        print(f"Error: {e}")
