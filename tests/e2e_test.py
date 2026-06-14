"""End-to-end test for Retro Alpha API."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force mock LLM mode before importing app (avoids loading 2.8GB model)
import agents
agents._llm = "mock"

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

r = client.get("/static/style.css")
check("style.css 200", r.status_code == 200)
check("style.css has scanlines", "scanlines" in r.text)

r = client.get("/static/app.js")
check("app.js 200", r.status_code == 200)
check("app.js has loadState", "loadState" in r.text)

r = client.get("/static/index.html")
check("static index.html 200", r.status_code == 200)

print("\n=== Initial state ===")
r = client.get("/api/state")
check("state 200", r.status_code == 200)
s = r.json()
check("year is 1994", s["year"] == 1994, f"got {s['year']}")
check("month is 4", s["month"] == 4, f"got {s['month']}")
check("cash is 1,000,000", s["cash"] == 1_000_000, f"got {s['cash']}")
check("total_value is 1,000,000", s["total_value"] == 1_000_000)
check("prices has Nifty 50", "Nifty 50" in s["prices"])
check("prices has Gold", "Gold" in s["prices"])
check("portfolio has Cash", "Cash" in s["portfolio"])
check("portfolio has Nifty 50", "Nifty 50" in s["portfolio"])
check("game_over false", s["game_over"] is False)
check("agent_actions is list", isinstance(s["agent_actions"], list))
check("agent_actions empty initially", len(s["agent_actions"]) == 0)
check("goal_year is 2004", s["goal_year"] == 2004)
check("goal_value is 2M", s["goal_value"] == 2_000_000)

print("\n=== Trades ===")
tradable = ["Nifty 50", "Nifty IT", "FD", "Gov Bonds", "Real Estate", "Crypto", "Gold"]
for asset in tradable:
    r = client.post("/api/trade", json={"asset": asset, "action": "buy", "amount_pct": 10})
    check(f"buy {asset} 10% 200", r.status_code == 200, f"got {r.status_code}: {r.json()}")
    s = r.json()
    check(f"  cash decreased for {asset}", s["cash"] < 1_000_000, f"cash={s['cash']}")
    # reset between trades
    client.post("/api/reset")

# Regression: exact value the user typed (15%)
r = client.post("/api/trade", json={"asset": "Nifty 50", "action": "buy", "amount_pct": 15})
check("buy Nifty 50 15% (user-reported)", r.status_code == 200, f"got {r.status_code}: {r.json()}")
s = r.json()
check("  cash ~850k after 15%", abs(s["cash"] - 850_000) < 1000, f"cash={s['cash']}")

print("\n=== Invalid trades ===")
r = client.post("/api/trade", json={"asset": "Cash", "action": "buy", "amount_pct": 10})
check("buy Cash rejected", r.status_code == 400, f"got {r.status_code}")

r = client.post("/api/trade", json={"asset": "Banana", "action": "buy", "amount_pct": 10})
check("buy Banana rejected", r.status_code == 400, f"got {r.status_code}")

r = client.post("/api/trade", json={"asset": "Nifty 50", "action": "hold", "amount_pct": 10})
check("invalid action rejected", r.status_code == 400, f"got {r.status_code}")

r = client.post("/api/trade", json={"asset": "Nifty 50", "action": "buy", "amount_pct": 150})
check("amount > 100 rejected", r.status_code == 400, f"got {r.status_code}")

r = client.post("/api/trade", json={"asset": "Nifty 50", "action": "buy", "amount_pct": 0})
check("amount = 0 rejected", r.status_code == 400, f"got {r.status_code}")

print("\n=== Advance month ===")
client.post("/api/reset")
r = client.post("/api/advance")
check("advance 200", r.status_code == 200)
s = r.json()
check("months_elapsed is 1", s["months_elapsed"] == 1)
check("agent_actions populated", len(s["agent_actions"]) > 0, f"got {len(s['agent_actions'])}")
if s["agent_actions"]:
    a = s["agent_actions"][0]
    check("agent has name", "agent" in a and a["agent"])
    check("agent has action", "action" in a)
    check("agent has asset (display name)", "asset" in a and a["asset"] in [
        "FD", "Gov Bonds", "Nifty 50", "Nifty IT", "Real Estate", "Crypto", "Gold"
    ], f"got asset={a.get('asset')}")
check("news has headline", s["news"] and s["news"].get("headline"), f"news={s['news']}")

print("\n=== Regression: response values are native Python floats (no numpy) ===")
for asset, val in s["prices"].items():
    check(f"price[{asset}] is float", type(val) is float, f"got {type(val).__name__}")
check("total_value is float", type(s["total_value"]) is float, f"got {type(s['total_value']).__name__}")
check("cash is float", type(s["cash"]) is float, f"got {type(s['cash']).__name__}")

print("\n=== Regression: forced LLM failure returns 200, not 500 ===")
client.post("/api/reset")
import agents as _agents
_orig_generate_news = _agents.generate_news
def _boom(*a, **kw):
    raise RuntimeError("simulated LLM crash")
_agents.generate_news = _boom
try:
    r = client.post("/api/advance")
    check("advance survives LLM crash with 200", r.status_code == 200, f"got {r.status_code}")
    s2 = r.json()
    check("months_elapsed still incremented", s2["months_elapsed"] == 1)
    check("prices still all float", all(type(v) is float for v in s2["prices"].values()))
finally:
    _agents.generate_news = _orig_generate_news

# Mentor crash resilience
def _boom_mentor(*a, **kw):
    raise RuntimeError("mentor crash")
_orig_mentor = app_module.mentor.generate_review
app_module.mentor.generate_review = _boom_mentor
try:
    r = client.get("/api/mentor")
    check("mentor survives crash with 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    check("mentor returns review dict", "review" in data and "roast" in data["review"])
finally:
    app_module.mentor.generate_review = _orig_mentor
client.post("/api/reset")

print("\n=== Multi-month advance ===")
client.post("/api/reset")
for i in range(12):
    r = client.post("/api/advance")
    s = r.json()
    if s["game_over"]:
        break
check("year rolled to 1995 after 12 months", s["year"] == 1995, f"year={s['year']} month={s['month']}")
check("month is 4 after full year", s["month"] == 4, f"month={s['month']}")
check("months_elapsed is 12", s["months_elapsed"] == 12)

print("\n=== Mentor review ===")
r = client.get("/api/mentor")
check("mentor 200", r.status_code == 200)
data = r.json()
check("mentor has review", "review" in data)
check("mentor review has roast", "roast" in data["review"])
check("mentor review has lesson", "lesson" in data["review"])
check("mentor review has suggestion", "suggestion" in data["review"])
# No raw parse error leaks
rev = data["review"]
check("roast is not raw parse error", rev["roast"] != "Could not parse review.")
check("no 'Parse error' in lesson", "Parse error" not in rev.get("lesson", ""))

print("\n=== Mentor fallback (forced empty LLM) returns real roast ===")
_orig_gen = app_module.mentor.generate
def _empty_llm(summary):
    return app_module.mentor.parse_mentor_response("", summary)
app_module.mentor.generate_review = _empty_llm
try:
    r = client.get("/api/mentor")
    check("mentor fallback 200", r.status_code == 200)
    rev2 = r.json()["review"]
    check("fallback roast is real (not parse error)", rev2["roast"] != "Could not parse review.")
    check("fallback roast non-empty", len(rev2["roast"]) > 0)
    check("fallback suggestion non-empty", len(rev2["suggestion"]) > 0)
finally:
    app_module.mentor.generate_review = _orig_gen

print("\n=== Reset ===")
r = client.post("/api/reset")
check("reset 200", r.status_code == 200)
check("reset to months_elapsed 0", r.json()["months_elapsed"] == 0)

print("\n=== Game over flow ===")
client.post("/api/reset")
# Run all 120 months
s = None
for i in range(120):
    r = client.post("/api/advance")
    s = r.json()
    if s["game_over"]:
        break
check("game_over after 120 advances", s["game_over"] is True, f"game_over={s['game_over']}")
check("year is 2004 at end", s["year"] == 2004, f"year={s['year']}")
check("month is 4 at end", s["month"] == 4, f"month={s['month']}")
check("months_elapsed is 120", s["months_elapsed"] == 120)

# Advance when game over should just return state
r2 = client.post("/api/advance")
check("advance when over returns same state", r2.status_code == 200)
check("still game_over", r2.json()["game_over"] is True)

print(f"\n{'='*40}")
print(f"PASSED: {PASSED}  FAILED: {FAILED}")
print(f"{'='*40}")
if FAILED:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL E2E TESTS PASSED")
