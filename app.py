"""
Retro Alpha — FastAPI backend with custom CRT terminal frontend.
Serves static assets and exposes game API endpoints.
"""

import os
import random
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import agents
import download_model
import engine
import mentor

ASSET_DISPLAY = {
    "cash": "Cash",
    "fd": "FD",
    "gov_bonds": "Gov Bonds",
    "nifty_50": "Nifty 50",
    "nifty_it": "Nifty IT",
    "real_estate": "Real Estate",
    "crypto": "Crypto",
    "gold": "Gold",
}
TRADABLE_ALIASES = {v: k for k, v in ASSET_DISPLAY.items() if k != "cash"}

# Ensure model is available locally
try:
    agents.MODEL_PATH = download_model.download()
except Exception as e:
    print(f"Model download failed: {e}. Will use mock mode if no local model exists.")

app = FastAPI(title="Retro Alpha")
ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

# Mount static files so /static/style.css and /static/app.js resolve
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory game state (single-player)
_game_state = engine.new_game()


def _flatten_agent_action(raw: Dict) -> Dict:
    if not raw:
        return {"agent": "", "action": "hold", "asset": "", "amount_pct": 0.0,
                "reason": "", "sentiment": ""}
    first = (raw.get("actions") or [{}])[0]
    return {
        "agent": raw.get("agent", ""),
        "action": first.get("action", "hold"),
        "asset": ASSET_DISPLAY.get(first.get("asset", ""), first.get("asset", "")),
        "amount_pct": first.get("amount_pct", 0.0),
        "reason": first.get("reason", ""),
        "sentiment": raw.get("sentiment", ""),
    }


def _translate_state(s: engine.GameState) -> Dict:
    return {
        "month": s.month,
        "year": s.year,
        "months_elapsed": s.months_elapsed,
        "goal_year": engine.STARTING_YEAR + engine.GAME_LENGTH_MONTHS // 12,
        "goal_value": engine.WIN_THRESHOLD,
        "prices": {ASSET_DISPLAY[k]: v for k, v in s.prices.items()},
        "portfolio": {ASSET_DISPLAY[k]: v for k, v in s.portfolio.items()},
        "cash": s.cash_balance,
        "total_value": s.total_value(),
        "news": s.news,
        "agent_actions": [_flatten_agent_action(a) for a in s.agent_actions],
        "game_over": s.game_over,
        "won": s.won,
    }


@app.get("/", response_class=HTMLResponse)
async def homepage():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/state")
def get_state() -> JSONResponse:
    return JSONResponse(_translate_state(_game_state))


@app.post("/api/trade")
async def make_trade(request: Request) -> JSONResponse:
    data = await request.json()
    asset_alias = data.get("asset")
    action = data.get("action")
    amount_pct = float(data.get("amount_pct", 0))

    if _game_state.game_over:
        return JSONResponse({"error": "Game over"}, status_code=400)

    asset_key = TRADABLE_ALIASES.get(asset_alias)
    if not asset_key:
        return JSONResponse(
            {"error": f"Invalid asset: {asset_alias}"}, status_code=400
        )
    if action not in ("buy", "sell"):
        return JSONResponse({"error": "Invalid action"}, status_code=400)
    if amount_pct <= 0 or amount_pct > 100:
        return JSONResponse({"error": "Amount must be between 0 and 100%"}, status_code=400)

    try:
        engine.execute_player_trade(_game_state, asset_key, action, amount_pct / 100.0)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse(_translate_state(_game_state))


@app.post("/api/advance")
def advance_turn() -> JSONResponse:
    if _game_state.game_over:
        return JSONResponse(_translate_state(_game_state))

    regime = random.choice(engine.REGIMES)
    news = agents.generate_news(regime)
    state_snapshot = {
        "month": _game_state.month,
        "year": _game_state.year,
        "prices": _game_state.prices,
        "portfolio": _game_state.portfolio,
        "cash": _game_state.cash_balance,
        "total_value": _game_state.total_value(),
        "news": _game_state.news,
        "agent_actions": _game_state.agent_actions,
    }
    agent_actions = agents.all_agents_decide(state_snapshot)
    engine.advance_month(_game_state, news, agent_actions)
    return JSONResponse(_translate_state(_game_state))


@app.get("/api/mentor")
def get_mentor_review() -> JSONResponse:
    summary = engine.year_end_summary(_game_state)
    review = mentor.generate_review(summary)
    return JSONResponse({"summary": summary, "review": review})


@app.post("/api/reset")
def reset_game() -> JSONResponse:
    global _game_state
    _game_state = engine.new_game()
    return JSONResponse(_translate_state(_game_state))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "7860")),
    )
