"""
Retro Alpha — FastAPI backend with custom CRT terminal frontend.
Serves static assets and exposes game API endpoints.
"""

import os
import random
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import agents
import download_model
import engine
import mentor

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


@app.get("/", response_class=HTMLResponse)
async def homepage():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/state")
def get_state() -> JSONResponse:
    return JSONResponse({
        "month": _game_state.month,
        "year": _game_state.year,
        "prices": _game_state.prices,
        "portfolio": _game_state.portfolio,
        "cash": _game_state.cash_balance,
        "total_value": _game_state.total_value(),
        "news": _game_state.news,
        "agent_actions": _game_state.agent_actions,
        "game_over": _game_state.game_over,
        "won": _game_state.won,
    })


@app.post("/api/trade")
async def make_trade(request: Request) -> JSONResponse:
    data = await request.json()
    asset = data.get("asset")
    action = data.get("action")
    amount_pct = float(data.get("amount_pct", 0))

    if _game_state.game_over:
        return JSONResponse({"error": "Game over"}, status_code=400)
    if asset not in engine.ASSETS:
        return JSONResponse({"error": "Invalid asset"}, status_code=400)

    engine.execute_player_trade(_game_state, asset, action, amount_pct)
    return await get_state()


@app.post("/api/advance")
def advance_turn() -> JSONResponse:
    if _game_state.game_over:
        return get_state()

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
    return get_state()


@app.get("/api/mentor")
def get_mentor_review() -> JSONResponse:
    summary = engine.year_end_summary(_game_state)
    review = mentor.generate_review(summary)
    return JSONResponse({"summary": summary, "review": review})


@app.post("/api/reset")
def reset_game() -> JSONResponse:
    global _game_state
    _game_state = engine.new_game()
    return get_state()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "7860")),
    )
