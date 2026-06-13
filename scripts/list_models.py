"""List available models on the configured API."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("ZENMUX_API_KEY")
BASE_URL = os.getenv("BASE_URL") or os.getenv("ZENMUX_BASE_URL")

headers = {"Authorization": f"Bearer {API_KEY}"}

try:
    resp = requests.get(f"{BASE_URL}/models", headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    print(resp.text[:2000])
except Exception as e:
    print(f"Error: {e}")
