"""Verify mock/deterministic mode works correctly (no LLM dependency)."""

import os
import sys
import time
import socket

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = 7861
BASE_URL = f"http://localhost:{PORT}"
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

PASSED = 0
FAILED = 0


def check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS: {name}")
    else:
        FAILED += 1
        print(f"  FAIL: {name} {detail}")


def wait_for_http(url, timeout=30):
    import urllib.request
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                r.read(1)
                return True
        except Exception as e:
            last = e
            time.sleep(0.3)
    print(f"  (wait_for_http timed out: {last})")
    return False


# Clear cached modules to pick up fresh agents.py without llama-cpp
for mod in list(sys.modules):
    if mod in ("app", "agents", "mentor", "engine", "events"):
        del sys.modules[mod]

import uvicorn
import app as app_module

print("Starting server (deterministic / mock mode)...")
config = uvicorn.Config(app_module.app, host="127.0.0.1", port=PORT, log_level="warning")
server = uvicorn.Server(config)
import threading
thread = threading.Thread(target=server.run, daemon=True)
thread.start()

if not wait_for_http(BASE_URL + "/", timeout=20):
    print("Server failed to start. Stopping.")
    server.should_exit = True
    sys.exit(1)
time.sleep(1.0)
print("Server ready.\n")

try:
    import urllib.request, json
    with urllib.request.urlopen(BASE_URL + "/api/health", timeout=5) as r:
        health = json.loads(r.read().decode())
    print(f"  /api/health response: {json.dumps(health, indent=2)}\n")
    check("health.llm is 'mock' (deterministic mode)",
          health.get("llm") == "mock", f"got '{health.get('llm')}'")
    check("health status ok", health.get("status") == "ok")

    # Chat via deterministic fallback
    req = urllib.request.Request(BASE_URL + "/api/chat", method="POST",
                                 data=json.dumps({"message": "Should I buy Nifty?", "snapshot": {
                                     "cash": 500000, "total_value": 1000000, "unrealized_pnl": 0,
                                     "positions": [],
                                 }}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        chat = json.loads(r.read().decode())
    print(f"  chat reply: '{chat.get('reply', '')[:120]}'")
    check("chat returned a reply", len(chat.get("reply", "").strip()) > 0)
    check("chat did NOT leak sentinel",
          "error: format only" not in chat.get("reply", ""),
          f"chat='{chat.get('reply', '')[:120]}'")
    check("chat reply is a real sentence",
          len(chat.get("reply", "").split()) >= 4, f"chat='{chat.get('reply', '')[:120]}'")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1500, "height": 950}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(0.5)

        status_text = page.locator("#status-line").inner_text()
        print(f"  status-line: '{status_text}'")
        check("status-line shows mock mode",
              "mock" in status_text.lower() or "deterministic" in status_text.lower() or "fallback" in status_text.lower(),
              f"status='{status_text}'")

        llm_tag = page.locator("#llm-status").inner_text()
        print(f"  topbar tag: '{llm_tag}'")
        check("topbar shows MOCK status", "MOCK" in llm_tag or "FALLBACK" in llm_tag,
              f"tag='{llm_tag}'")

        page.fill("#chat-input", "Should I buy Nifty?")
        page.click("#chat-form button")
        page.wait_for_function(
            "() => document.getElementById('chat-log').children.length >= 1",
            timeout=8000,
        )
        chat_text = page.locator("#chat-log").inner_text()
        check("chat UI reply non-empty", len(chat_text.strip()) > 0)
        check("chat UI no sentinel leak", "error: format only" not in chat_text)

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "mock_mode.png"), full_page=True)
        browser.close()
finally:
    server.should_exit = True
    time.sleep(0.5)

print(f"\n{'='*60}")
print(f"VERIFY MOCK MODE — PASSED: {PASSED}  FAILED: {FAILED}")
print(f"{'='*60}")
if FAILED:
    sys.exit(1)
print("ALL CHECKS PASSED — deterministic mock mode works correctly.")
