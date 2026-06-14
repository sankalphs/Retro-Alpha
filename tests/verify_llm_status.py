"""Verify the LLM error reason reaches the UI when the model can't load.

This is the exact scenario the user is hitting on the Space: the model
file is missing (download failed / not present), so get_llm() raises.
We simulate it WITHOUT triggering a real 2.84 GB download by injecting
a fake download_model that returns a nonexistent path.

Confirms:
  - /api/health returns llm='error' (not 'uninitialized') and a non-empty
    llm_error describing the real failure
  - the frontend status line shows the real error (not the generic
    'model not loaded' fallback)
  - chat still works via deterministic fallback (no 'error: format only'
    sentinel leak)
"""

import os
import sys
import time
import socket
import types

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PORT = 7861
BASE_URL = f"http://localhost:{PORT}"
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
FAKE_MISSING = os.path.join(MODEL_DIR, "FAKE_MISSING_MODEL.gguf")

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
    """Wait until the URL returns any HTTP response (not just port open)."""
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


# Clear cached modules
for mod in list(sys.modules):
    if mod in ("app", "agents", "download_model", "mentor", "engine", "events"):
        del sys.modules[mod]

# Inject fake download_model -> returns nonexistent path
fake_dm = types.ModuleType("download_model")
fake_dm.download = lambda: FAKE_MISSING
fake_dm.MODEL_REPO = "fake/repo"
fake_dm.MODEL_FILE = "fake.gguf"
fake_dm.MODEL_DIR = MODEL_DIR
sys.modules["download_model"] = fake_dm

# Ensure MOCK_LLM is off so the real llama_cpp loader runs (and fails)
for k in ("MOCK_LLM", "HF_TOKEN", "MODEL_PATH"):
    os.environ.pop(k, None)

import uvicorn
import app as app_module  # noqa: E402

print("Starting server (MOCK_LLM=0, fake missing model)...")
config = uvicorn.Config(app_module.app, host="127.0.0.1", port=PORT, log_level="warning")
server = uvicorn.Server(config)
import threading
thread = threading.Thread(target=server.run, daemon=True)
thread.start()

if not wait_for_http(BASE_URL + "/", timeout=20):
    print("Server failed to start. Stopping.")
    server.should_exit = True
    sys.exit(1)
time.sleep(1.0)  # let eager get_llm() complete (FileNotFoundError is instant)
print("Server ready.\n")

try:
    import urllib.request, json
    with urllib.request.urlopen(BASE_URL + "/api/health", timeout=5) as r:
        health = json.loads(r.read().decode())
    print(f"  /api/health response: {json.dumps(health, indent=2)}\n")
    check("health.llm is 'error' (real load was attempted)",
          health.get("llm") == "error", f"got '{health.get('llm')}'")
    check("health.llm_error is NON-EMPTY (real reason)",
          bool(health.get("llm_error")), f"got '{health.get('llm_error')}'")
    check("health.llm_error mentions the file or the path",
          "FAKE_MISSING" in str(health.get("llm_error", "")) or "not found" in str(health.get("llm_error", "")).lower(),
          f"err='{health.get('llm_error')}'")
    check("health.model_exists is False",
          health.get("model_exists") is False)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1500, "height": 950}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(0.5)

        status_text = page.locator("#status-line").inner_text()
        print(f"  status-line: '{status_text}'")
        check("status-line shows 'LLM offline'", "offline" in status_text.lower())
        check("status-line does NOT show generic 'model not loaded' fallback",
              "model not loaded" not in status_text.lower(),
              f"status='{status_text}'")
        check("status-line mentions the fake model path (real error)",
              "FAKE_MISSING" in status_text,
              f"status='{status_text}'")

        llm_tag = page.locator("#llm-status").inner_text()
        check("topbar shows OFFLINE", "OFFLINE" in llm_tag)
        tip = page.locator("#llm-status").get_attribute("title") or ""
        check("topbar tooltip has real error", len(tip) > 10 and "FAKE" in tip,
              f"tooltip='{tip}'")

        # Chat via deterministic fallback (no 'error: format only' leak)
        page.fill("#chat-input", "Should I buy Nifty?")
        page.click("#chat-form button")
        page.wait_for_function(
            "() => document.getElementById('chat-log').children.length >= 1",
            timeout=8000,
        )
        chat_text = page.locator("#chat-log").inner_text()
        print(f"  chat reply: '{chat_text[:120]}'")
        check("chat returned a reply", len(chat_text.strip()) > 0)
        check("chat did NOT leak 'error: format only'",
              "error: format only" not in chat_text,
              f"chat='{chat_text[:120]}'")
        check("chat reply is a real, useful sentence",
              len(chat_text.split()) >= 4, f"chat='{chat_text[:120]}'")

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "llm_missing.png"), full_page=True)
        browser.close()
finally:
    server.should_exit = True
    time.sleep(0.5)

print(f"\n{'='*60}")
print(f"VERIFY LLM STATUS — PASSED: {PASSED}  FAILED: {FAILED}")
print(f"{'='*60}")
if FAILED:
    sys.exit(1)
print("ALL CHECKS PASSED — the real LLM error reason reaches the UI.")
