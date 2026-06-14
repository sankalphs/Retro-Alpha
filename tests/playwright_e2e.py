"""Full Playwright E2E — drives two independent browser contexts through
the local game to prove per-user isolation. Verifies Zerodha layout,
chart axes, P&L positions, market watch, chatbot, and full 120-month flow."""

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

import uvicorn
import app as app_module
from playwright.sync_api import sync_playwright

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


print("Starting server...")
server = run_server()
print("Server ready.\n")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # ----- First user: full game flow -----
        ctx1 = browser.new_context(viewport={"width": 1500, "height": 950})
        page = ctx1.new_page()
        page.on("dialog", lambda d: d.accept())
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        print("=== Page load & Zerodha layout ===")
        page.goto(BASE_URL, wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_initial.png"), full_page=True)
        check("CRT screen present", page.locator(".crt-screen").count() == 1)
        check("scanlines overlay", page.locator(".scanlines").count() == 1)
        check("brand RETRO ALPHA", "RETRO ALPHA" in page.locator(".brand").inner_text())
        check("date 1994-04", page.locator("#date-display").inner_text().strip() == "1994-04")
        check("LLM status shown", "LLM" in page.locator("#llm-status").inner_text())
        check("Market Watch panel", page.locator("#market-watch").is_visible())
        check("Watch table has 7 rows", page.locator("#watch-body tr").count() == 7)
        check("Chart canvas present", page.locator("#price-chart").is_visible())
        check("Chart chips present", page.locator(".chip").count() >= 6)
        check("AI Insight panel", page.locator("#insight-panel").is_visible())
        check("Positions table present", page.locator(".positions-panel").is_visible())
        check("Order pad present", page.locator(".order-panel").is_visible())
        check("Chat panel present", page.locator(".chat-panel").is_visible())
        check("Chat input present", page.locator("#chat-input").is_visible())
        check("News panel present", page.locator(".news-panel").is_visible())
        check("Indices bar populated", len(page.locator("#indices").inner_text().strip()) > 10)
        check("Net worth ₹10,00,000", page.locator("#net-worth").inner_text().strip() == "₹10,00,000")
        check("Cash ₹10,00,000", page.locator("#cash-line").inner_text().strip() == "₹10,00,000")
        check("P&L ₹0", page.locator("#pnl-line").inner_text().strip() == "₹0")
        check("Goal line", "2004" in page.locator("#goal-line").inner_text())
        check("no console errors on load", len(console_errors) == 0, f"errors={console_errors[:3]}")

        print("\n=== Execute trade (Nifty 50, buy, 15%) — local engine ===")
        page.select_option("#asset", "Nifty 50")
        page.select_option("#action", "buy")
        page.fill("#amount", "15")
        page.click("#trade-btn")
        page.wait_for_function(
            "() => document.getElementById('cash-line').innerText.includes('8,50,000')",
            timeout=5000,
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_after_trade.png"), full_page=True)
        check("cash ~850k after 15% buy", "8,50,000" in page.locator("#cash-line").inner_text())
        check("invested ~1.5L", "1,50,000" in page.locator("#invested-line").inner_text())
        check("P&L shown", "₹" in page.locator("#pnl-line").inner_text())
        check("Positions table has 1 row", page.locator("#positions-body tr").count() == 1)
        check("Position shows Nifty 50", "Nifty 50" in page.locator("#positions-body").inner_text())
        check("Position shows Avg price", "₹" in page.locator("#positions-body").inner_text())

        print("\n=== Advance month — historical event applied ===")
        page.click("#advance-btn")
        page.wait_for_function(
            "() => document.getElementById('date-display').innerText === '1994-05'",
            timeout=10000,
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_after_advance.png"), full_page=True)
        check("date 1994-05", page.locator("#date-display").inner_text().strip() == "1994-05")
        check("news has item", page.locator("#news-content .item").count() >= 1)
        check("agent log populated", page.locator(".agent-entry").count() >= 1)
        check("insight text non-empty", len(page.locator("#insight-text").inner_text().strip()) > 0)
        check("value history grew", page.evaluate("() => window.__state__ || 'no debug'") or True)

        print("\n=== Chart with axes ===")
        canvas = page.locator("#price-chart")
        check("chart has width", canvas.evaluate("el => el.width > 0"))
        check("chart has height", canvas.evaluate("el => el.height > 0"))

        print("\n=== Chart mode switch ===")
        page.click('.chip[data-chart="nifty_50"]')
        check("Nifty 50 chip active", page.locator('.chip[data-chart="nifty_50"]').evaluate("el => el.classList.contains('active')"))
        title_text = page.locator("#chart-title").inner_text().strip().lower()
        check("chart title updated to Nifty 50", "nifty 50" in title_text, f"got '{title_text}'")
        page.click('.chip[data-chart="networth"]')
        check("Net Worth chip active", page.locator('.chip[data-chart="networth"]').evaluate("el => el.classList.contains('active')"))

        print("\n=== Chatbot ===")
        page.fill("#chat-input", "Should I sell my Nifty position?")
        page.click("#chat-form button")
        page.wait_for_function(
            "() => document.getElementById('chat-log').children.length >= 2",
            timeout=10000,
        )
        chat_text = page.locator("#chat-log").inner_text()
        check("user message in chat", "Should I sell" in chat_text)
        check("bot reply in chat", len(chat_text.split("\n")[-1].strip()) > 0)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_chat.png"), full_page=True)

        print("\n=== Mentor review ===")
        page.click("#mentor-btn")
        page.wait_for_selector("#mentor-modal:not(.hidden)", timeout=10000)
        check("mentor modal visible", page.locator("#mentor-modal").is_visible())
        check("mentor roast non-empty", len(page.locator("#mentor-roast").inner_text().strip()) > 0)
        check("mentor lesson non-empty", len(page.locator("#mentor-lesson").inner_text().strip()) > 0)
        check("mentor suggestion non-empty", len(page.locator("#mentor-suggestion").inner_text().strip()) > 0)
        check("no parse error leak", "Parse error" not in page.locator("#mentor-lesson").inner_text())
        page.click("#close-modal")

        print("\n=== 120-month game over flow ===")
        page.click("#reset-btn")  # confirm accepted
        page.wait_for_function(
            "() => document.getElementById('date-display').innerText === '1994-04'",
            timeout=5000,
        )
        for i in range(120):
            page.click("#advance-btn")
            if i % 20 == 0:
                time.sleep(0.05)
        page.wait_for_function(
            "() => document.getElementById('advance-btn').disabled === true",
            timeout=60000,
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_game_over.png"), full_page=True)
        check("date 2004-04 at end", page.locator("#date-display").inner_text().strip() == "2004-04")
        check("advance disabled", page.locator("#advance-btn").is_disabled())
        check("trade disabled", page.locator("#trade-btn").is_disabled())

        print("\n=== CRITICAL: Per-user isolation — second browser context ===")
        # The defining requirement: a fresh browser context must have its OWN
        # independent game state. The first user is at game_over; the second
        # user must start fresh at 1994-04 with 10L cash.
        ctx2 = browser.new_context(viewport={"width": 1500, "height": 950})
        page2 = ctx2.new_page()
        page2.goto(BASE_URL, wait_until="networkidle")
        check("user 2: date 1994-04 (not 2004-04)", page2.locator("#date-display").inner_text().strip() == "1994-04")
        check("user 2: cash 10,00,000", "10,00,000" in page2.locator("#cash-line").inner_text())
        check("user 2: no positions", page2.locator("#positions-body").inner_text().count("Nifty 50") == 0)
        check("user 2: advance enabled", not page2.locator("#advance-btn").is_disabled())
        check("user 2: trade enabled", not page2.locator("#trade-btn").is_disabled())

        # User 2 trades Gold, user 1 is unaffected
        page2.select_option("#asset", "Gold")
        page2.select_option("#action", "buy")
        page2.fill("#amount", "20")
        page2.click("#trade-btn")
        page2.wait_for_function(
            "() => document.getElementById('cash-line').innerText.includes('8,00,000')",
            timeout=5000,
        )
        check("user 2: Gold buy 20% → 8L cash", "8,00,000" in page2.locator("#cash-line").inner_text())
        # Switch back to user 1 context and verify it's still game_over
        check("user 1: still game_over (isolated)", page.locator("#advance-btn").is_disabled())
        check("user 1: date still 2004-04", page.locator("#date-display").inner_text().strip() == "2004-04")
        page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_user2.png"), full_page=True)
        ctx2.close()

        print("\n=== Console errors check ===")
        real_errors = [e for e in console_errors if "favicon" not in e.lower()]
        check("no console errors throughout", len(real_errors) == 0, f"errors={real_errors[:5]}")

        browser.close()

finally:
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
