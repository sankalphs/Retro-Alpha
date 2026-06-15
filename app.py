"""
Retro Alpha - 90s Indian Stock Market Survival Game
Gradio app for HuggingFace Spaces (Build Small Hackathon).

Game engine runs 100% in the browser.
Server handles LLM-backed features: chat, mentor, insight.
No per-user state; every browser tab is independent.
"""

import os
from pathlib import Path

import gradio as gr
from fastapi import Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import agents
import mentor as _mentor

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"


def get_full_html():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


with gr.Blocks(
    title="Retro Alpha",
    fill_width=True,
    fill_height=True,
    css="""
    .gradio-container { max-width: 100% !important; margin: 0 !important; padding: 0 !important; }
    .contain { padding: 0 !important; max-width: none !important; }
    .main { padding: 0 !important; }
    footer { display: none !important; }
    #retro-root { width: 100vw; height: 100vh; overflow: hidden; }
    #retro-root iframe { width: 100%; height: 100%; border: none; }
    """,
) as demo:
    full_html = get_full_html()
    gr.HTML(full_html, elem_id="retro-root")

app = demo.app
app.mount("/game", StaticFiles(directory=str(STATIC_DIR)), name="game_static")


@app.get("/game-api/health")
def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "llm": agents.llm_status(),
        "llm_error": agents.llm_error(),
    })


@app.post("/game-api/chat")
async def chat(request: Request) -> JSONResponse:
    data = await request.json()
    user_message = str(data.get("message", "")).strip()
    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)
    snapshot = data.get("snapshot") or {}
    try:
        reply = agents.chat_reply(user_message, snapshot)
    except Exception as e:
        print(f"Chat error: {e}")
        reply = "I'm having trouble thinking right now. Try again in a moment."
    return JSONResponse({"reply": reply})


@app.post("/game-api/insight")
async def insight(request: Request) -> JSONResponse:
    data = await request.json()
    event = data.get("event") or {}
    snapshot = data.get("snapshot") or {}
    try:
        text = agents.generate_insight(event, snapshot)
    except Exception as e:
        print(f"Insight error: {e}")
        text = ""
    return JSONResponse({"insight": text})


@app.post("/game-api/mentor")
async def mentor_review(request: Request) -> JSONResponse:
    data = await request.json()
    summary = data.get("summary") or {}
    try:
        review = _mentor.generate_review(summary)
    except Exception as e:
        print(f"Mentor error: {e}")
        review = {
            "roast": "Markets are noisy; so is my parser.",
            "sharpe_ratio": 0.0,
            "lesson": "Sharpe ratio measures risk-adjusted return.",
            "suggestion": "Diversify across asset classes.",
        }
    return JSONResponse({"review": review})


def launch():
    agents.start_background_load()
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        favicon_path=None,
        show_error=True,
    )


if __name__ == "__main__":
    launch()
