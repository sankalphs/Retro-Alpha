"""Single synchronous probe of the configured API."""

import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("ZENMUX_API_KEY")
BASE_URL = os.getenv("BASE_URL") or os.getenv("ZENMUX_BASE_URL")
MODEL = os.getenv("MODEL") or os.getenv("ZENMUX_MODEL")

print(f"BASE_URL: {BASE_URL}")
print(f"MODEL: {MODEL}")
print(f"Key length: {len(API_KEY) if API_KEY else 0}")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in JSON format with key 'message'."}
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

try:
    resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    print(f"Body: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
