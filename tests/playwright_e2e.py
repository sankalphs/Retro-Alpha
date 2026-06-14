"""Full Playwright E2E test — drives a real browser through the game."""

import os
import sys
import time
import socket

# Force UTF-8 stdout for ₹ symbol on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force mock LLM
os.environ["MOCK_LLM"] = "1"

import uvicorn
import app as app_module
from playwright.sync_api import sync_playwright, expect

PORT = 7860
BASE_URL = f"http://localhost:{PORT}"
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

PASSED = 0
FAILED = 0
ERRORS = []


def check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS: {name}")
    else:
        FAILED += 1
        print(f"  FAIL: {name} {detail}")
        ERRORS.append(f"{name}: {detail}")


def wait_for_port(port, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def run_server():
    config = uvicorn.Config(app_module.app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    import threading
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    if not wait_for_port(PORT, timeout=30):
        raise RuntimeError("Server failed to start")
    return server


print("Starting server (MOCK_LLM=1)...")
server = run_server()
print("Server ready.\n")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        # Auto-accept all confirm dialogs (used by reset button)
        page.on("dialog", lambda d: d.accept())

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("=== Page load & CRT UI ===")
        page.goto(BASE_URL, wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_initial.png"), full_page=True)

        check("title is Retro Alpha", "RETRO ALPHA" in page.title() or page.locator("text=RETRO ALPHA").count() > 0)
        check("CRT screen visible", page.locator(".crt-screen").is_visible())
        check("scanlines overlay present", page.locator(".scanlines").count() == 1)
        check("screen curve overlay", page.locator(".screen-curve").count() == 1)
        check("logo shows RETRO ALPHA", "RETRO ALPHA" in page.locator(".logo").inner_text())
        check("header date 1994-04", page.locator("#date-display").inner_text().strip() == "1994-04")
        check("net worth ₹10,00,000", page.locator("#net-worth").inner_text().strip() == "₹10,00,000")
        check("goal line shows 2M by 2004", "₹20,00,000" in page.locator("#goal-line").inner_text() and "2004" in page.locator("#goal-line").inner_text())
        check("online indicator", "ONLINE" in page.locator(".status-bar").inner_text())
        check("ticker has market data", len(page.locator("#ticker").inner_text().strip()) > 20)
        check("order pad present", page.locator("#trade-form").is_visible())
        check("holdings table present", page.locator("#holdings-table").is_visible())
        check("news panel present", page.locator(".news-panel").is_visible())
        check("agent wire present", page.locator("#agent-log").is_visible())
        check("chart canvas present", page.locator("#price-chart").is_visible())
        check("advance button", page.locator("#advance-btn").is_visible())
        check("mentor button", page.locator("#mentor-btn").is_visible())
        check("reset button", page.locator("#reset-btn").is_visible())
        check("no console errors on load", len(console_errors) == 0, f"errors={console_errors[:3]}")

        print("\n=== Execute trade (Nifty 50, buy, 15%) ===")
        page.select_option("#asset", "Nifty 50")
        page.select_option("#action", "buy")
        page.fill("#amount", "15")
        page.click("#trade-btn")
        # Wait for state to update — net worth should still be ~1M, cash ~850k
        page.wait_for_function(
            "() => document.getElementById('cash-line').innerText.includes('8,50,000')",
            timeout=5000,
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_after_trade.png"), full_page=True)

        cash_text = page.locator("#cash-line").inner_text()
        check("cash ~850k after 15% buy", "8,50,000" in cash_text, f"got '{cash_text}'")
        check("holdings show Nifty 50 row", page.locator("#holdings-table tbody tr").count() == 1)
        nifty_row = page.locator("#holdings-table tbody tr").first
        check("holdings asset name", nifty_row.locator("td").first.inner_text().strip() == "Nifty 50")
        check("no ALERT in news", "[ALERT]" not in page.locator("#news-content").inner_text())

        print("\n=== Try trade with 0% (HTML5 validation should block) ===")
        page.fill("#amount", "0")
        # Browser's built-in validation will block submit; no trade should execute
        page.click("#trade-btn")
        time.sleep(0.5)
        # Holdings should still be just Nifty 50 (from previous trade), no new row
        check("0% blocked by HTML5 validation (holdings unchanged)",
              page.locator("#holdings-table tbody tr").count() == 1)
        check("no ALERT shown (request never reached server)",
              "[ALERT]" not in page.locator("#news-content").inner_text())
        # Reset amount field to a valid value for next test
        page.fill("#amount", "15")

        print("\n=== Reset and execute valid trade again ===")
        page.click("#reset-btn")
        page.wait_for_function(
            "() => document.getElementById('cash-line').innerText.includes('10,00,000')",
            timeout=5000,
        )
        check("reset to 1994-04", page.locator("#date-display").inner_text().strip() == "1994-04")
        check("reset cash to 10,00,000", True)

        page.select_option("#asset", "Gold")
        page.select_option("#action", "buy")
        page.fill("#amount", "20")
        page.click("#trade-btn")
        page.wait_for_function(
            "() => document.getElementById('cash-line').innerText.includes('8,00,000')",
            timeout=5000,
        )
        check("bought Gold at 20%", "8,00,000" in page.locator("#cash-line").inner_text())

        print("\n=== Advance month ===")
        page.click("#advance-btn")
        page.wait_for_function(
            "() => document.getElementById('date-display').innerText === '1994-05'",
            timeout=10000,
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_after_advance.png"), full_page=True)
        check("date advanced to 1994-05", page.locator("#date-display").inner_text().strip() == "1994-05")
        check("agent wire populated", page.locator(".agent-entry").count() > 0, f"entries={page.locator('.agent-entry').count()}")
        check("news has headline", page.locator("#news-content .news-content div, #news-content > div").count() > 0)
        check("no ALERT after valid advance", "[ALERT]" not in page.locator("#news-content").inner_text())

        print("\n=== Advance 11 more months (year rollover) ===")
        for _ in range(11):
            page.click("#advance-btn")
            time.sleep(0.2)
        page.wait_for_function(
            "() => document.getElementById('date-display').innerText === '1995-04'",
            timeout=15000,
        )
        check("year rolled to 1995", page.locator("#date-display").inner_text().strip() == "1995-04")

        print("\n=== Year-End Review ===")
        page.click("#mentor-btn")
        page.wait_for_selector("#mentor-modal:not(.hidden)", timeout=5000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_mentor.png"), full_page=True)
        check("mentor modal visible", page.locator("#mentor-modal").is_visible())
        check("mentor has roast", len(page.locator("#mentor-roast").inner_text().strip()) > 0)
        check("mentor has lesson", len(page.locator("#mentor-lesson").inner_text().strip()) > 0)
        check("mentor has suggestion", len(page.locator("#mentor-suggestion").inner_text().strip()) > 0)
        page.click("#close-modal")
        page.wait_for_selector("#mentor-modal.hidden", timeout=2000)
        check("mentor modal closes", page.locator("#mentor-modal.hidden").count() == 1)

        print("\n=== Reset terminal ===")
        page.click("#reset-btn")
        page.wait_for_function(
            "() => document.getElementById('date-display').innerText === '1994-04'",
            timeout=5000,
        )
        check("reset to 1994-04", page.locator("#date-display").inner_text().strip() == "1994-04")
        check("cash back to 1M", "10,00,000" in page.locator("#cash-line").inner_text())

        print("\n=== Game over flow (120 advances) ===")
        for i in range(120):
            page.click("#advance-btn")
            if i % 20 == 0:
                time.sleep(0.1)
        # Wait for game over: ticker shows the end-of-game message
        page.wait_for_function(
            "() => document.getElementById('ticker').innerText.includes('COMPLETE')",
            timeout=60000,
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_game_over.png"), full_page=True)
        ticker_text = page.locator("#ticker").inner_text()
        check("game over reached (ticker COMPLETE)", "COMPLETE" in ticker_text, f"ticker='{ticker_text[:80]}'")
        check("date is 2004-04", page.locator("#date-display").inner_text().strip() == "2004-04")
        check("trade button disabled", page.locator("#trade-btn").is_disabled())

        print("\n=== Console errors check ===")
        # Filter out the 0% trade alert (we triggered it intentionally) - no, that's a news div not console
        real_errors = [e for e in console_errors if "favicon" not in e.lower()]
        check("no console errors throughout", len(real_errors) == 0, f"errors={real_errors[:5]}")

        browser.close()

finally:
    # Stop server
    try:
        server.should_exit = True
    except Exception:
        pass
    time.sleep(0.5)

print(f"\n{'='*50}")
print(f"PLAYWRIGHT E2E — PASSED: {PASSED}  FAILED: {FAILED}")
print(f"{'='*50}")
if FAILED:
    print("\nFailures:")
    for e in ERRORS:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL PLAYWRIGHT E2E TESTS PASSED")
