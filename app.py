"""
Retro Alpha — Gradio Server backend.
Serves a custom CRT terminal frontend and exposes game API endpoints.
"""

import random
from pathlib import Path

from fastapi.responses import HTMLResponse
from gradio import Server

import agents
import download_model
import engine
import mentor

# Ensure model is available locally
try:
    agents.MODEL_PATH = download_model.download()
except Exception as e:
    print(f"Model download failed: {e}. Will use mock mode if no local model exists.")

app = Server()
ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

# In-memory game state (single-player)
_game_state = engine.new_game()


@app.get("/", response_class=HTMLResponse)
async def homepage():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.api(name="state")
def get_state() -> dict:
    return {
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
    }


@app.api(name="trade")
def make_trade(asset: str, action: str, amount_pct: float) -> dict:
    if _game_state.game_over:
        return {"error": "Game over"}
    if asset not in engine.ASSETS:
        return {"error": "Invalid asset"}
    engine.execute_player_trade(_game_state, asset, action, amount_pct)
    return get_state()


@app.api(name="advance")
def advance_turn() -> dict:
    if _game_state.game_over:
        return get_state()

    # Generate news
    regime = random.choice(engine.REGIMES)  # noqa: F821
    news = agents.generate_news(regime)

    # Agents decide
    state_snapshot = get_state()
    agent_actions = agents.all_agents_decide(state_snapshot)

    # Advance
    engine.advance_month(_game_state, news, agent_actions)
    return get_state()


@app.api(name="mentor")
def get_mentor_review() -> dict:
    summary = engine.year_end_summary(_game_state)
    review = mentor.generate_review(summary)
    return {"summary": summary, "review": review}


@app.api(name="reset")
def reset_game() -> dict:
    global _game_state
    _game_state = engine.new_game()
    return get_state()


if __name__ == "__main__":
    app.launch(show_error=True)
