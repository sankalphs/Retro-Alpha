"""End-to-end test for Retro Alpha API (LLM endpoints only — game runs in browser)."""

import os
import sys
import types

# Force UTF-8 stdout for ₹ symbol on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force mock LLM for tests
os.environ["MOCK_LLM"] = "1"

# Inject a fake download_model so app.py startup does NOT try to
# download the 2.84 GB model from the Hub. The MOCK_LLM flag means
# the model is never loaded into RAM, so the path is irrelevant.
_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
_FAKE_PATH = os.path.join(os.path.abspath(_MODEL_DIR), "TEST_FAKE_IGNORED.gguf")
for mod in list(sys.modules):
    if mod in ("download_model",):
        del sys.modules[mod]
fake_dm = types.ModuleType("download_model")
fake_dm.download = lambda: _FAKE_PATH
fake_dm.MODEL_REPO = "fake/test"
fake_dm.MODEL_FILE = "fake.gguf"
fake_dm.MODEL_DIR = os.path.abspath(_MODEL_DIR)
sys.modules["download_model"] = fake_dm

import agents
agents._llm = "mock"
agents._llm_status = "mock"

from fastapi.testclient import TestClient
import app as app_module

client = TestClient(app_module.app)

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


print("=== Static assets ===")
r = client.get("/")
check("homepage 200", r.status_code == 200)
check("homepage has RETRO ALPHA", "RETRO ALPHA" in r.text)
check("homepage loads engine.js", "/static/engine.js" in r.text)
check("homepage loads events.js", "/static/events.js" in r.text)
check("homepage loads app.js", "/static/app.js" in r.text)
check("homepage loads style.css", "/static/style.css" in r.text)
check("homepage has chat panel", "chat-panel" in r.text)
check("homepage has positions table", "positions-table" in r.text)
check("homepage has market watch", "market-watch" in r.text)

r = client.get("/static/style.css")
check("style.css 200", r.status_code == 200)
check("style.css has scanlines", "scanlines" in r.text)
check("style.css has kite-grid", "kite-grid" in r.text)

r = client.get("/static/engine.js")
check("engine.js 200", r.status_code == 200)
check("engine.js has newGame", "newGame" in r.text)
check("engine.js has advanceMonth", "advanceMonth" in r.text)
check("engine.js has localAgentDecide", "localAgentDecide" in r.text)

r = client.get("/static/events.js")
check("events.js 200", r.status_code == 200)
check("events.js has eventForMonth", "eventForMonth" in r.text)
check("events.js has dot-com", "Dot-com" in r.text)
check("events.js has 9/11", "9/11" in r.text)

r = client.get("/static/app.js")
check("app.js 200", r.status_code == 200)
check("app.js uses RetroEngine", "RetroEngine" in r.text)

print("\n=== Health ===")
r = client.get("/api/health")
check("health 200", r.status_code == 200)
h = r.json()
check("health status ok", h.get("status") == "ok")
check("health reports llm", "llm" in h)

print("\n=== Game endpoints removed (state is local now) ===")
for ep in ["/api/state", "/api/trade", "/api/advance", "/api/reset"]:
    r = client.get(ep) if ep == "/api/state" else client.post(ep)
    check(f"{ep} returns 404 (removed)", r.status_code == 404, f"got {r.status_code}")

print("\n=== /api/chat ===")
r = client.post("/api/chat", json={"message": "should I buy Nifty?", "snapshot": {
    "cash": 500000, "total_value": 1000000, "unrealized_pnl": 0,
    "positions": [{"asset": "Gold", "qty": 1.0, "price": 3000, "value": 3000}],
}})
check("chat 200", r.status_code == 200)
data = r.json()
check("chat has reply", "reply" in data and len(data["reply"]) > 0)
# Regression: no raw "error: format only" leaks from the mock
check("chat never returns 'error: format only'",
      "error: format only" not in data["reply"], f"reply='{data['reply']}'")
check("chat reply looks like real commentary (has ₹ or words)",
      ("₹" in data["reply"] or len(data["reply"].split()) >= 4),
      f"reply='{data['reply']}'")

r = client.post("/api/chat", json={"message": "", "snapshot": {}})
check("empty message rejected", r.status_code == 400)

print("\n=== /api/insight ===")
r = client.post("/api/insight", json={
    "event": {"headline": "Test crash", "regime": "market_crash"},
    "snapshot": {"unrealized_pnl": -100000, "cash": 500000, "total_value": 900000},
})
check("insight 200", r.status_code == 200)
data = r.json()
check("insight has text", "insight" in data and len(data["insight"]) > 0)
check("insight never returns 'error: format only'",
      "error: format only" not in data["insight"], f"insight='{data['insight']}'")

print("\n=== /api/mentor ===")
r = client.post("/api/mentor", json={"summary": {
    "year": 1995, "month": 4, "starting_value": 1000000, "ending_value": 1500000,
    "invested_value": 800000, "cash": 700000, "unrealized_pnl": 200000,
    "max_drawdown": -0.15, "sharpe_ratio": 1.2,
    "allocations": {"fd": 0.2, "nifty_50": 0.4, "gold": 0.1, "crypto": 0.1},
}})
check("mentor 200", r.status_code == 200)
data = r.json()
rev = data.get("review", {})
check("mentor has roast", "roast" in rev and rev["roast"] != "Could not parse review.")
check("mentor has lesson", "lesson" in rev)
check("mentor has suggestion", "suggestion" in rev)
check("no Parse error leak", "Parse error" not in rev.get("lesson", ""))

print(f"\n{'='*40}")
print(f"PASSED: {PASSED}  FAILED: {FAILED}")
print(f"{'='*40}")
if FAILED:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL E2E TESTS PASSED")
