"""
Retro Alpha - 90s Indian Stock Market Survival Game
Gradio app for HuggingFace Spaces (Build Small Hackathon).

Serves a self-contained HTML page at root via an ASGI wrapper.
Gradio handles the API routes; root GET bypasses Gradio entirely.
"""
import os
from pathlib import Path

import gradio as gr
from fastapi import Request
from fastapi.responses import JSONResponse, HTMLResponse

import agents
import mentor as _mentor

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"


def _read(p: str) -> str:
    with open(STATIC_DIR / p, "r", encoding="utf-8") as f:
        return f.read()


_CSS = _read("style.css")
_HTML_BODY = _read("index.html")
_ENGINE_JS = _read("engine.js")
_EVENTS_JS = _read("events.js")
_APP_JS = _read("app.js")

PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Retro Alpha - 90s Market Terminal</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
<style>
{_CSS}
</style>
</head>
<body>
{_HTML_BODY}
<script>
{_EVENTS_JS}
</script>
<script>
{_ENGINE_JS}
</script>
<script>
{_APP_JS}
</script>
</body>
</html>"""


with gr.Blocks(title="Retro Alpha") as demo:
    pass

api = demo.app


@api.get("/game-api/health")
def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "llm": agents.llm_status(),
        "llm_error": agents.llm_error(),
    })


@api.post("/game-api/chat")
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


@api.post("/game-api/insight")
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


@api.post("/game-api/mentor")
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


# ASGI wrapper: intercept root GET before Gradio's router
_gradio_app = api


async def app(scope, receive, send):
    if scope["type"] == "http" and scope["method"] == "GET" and scope["path"] == "/":
        response = HTMLResponse(PAGE)
        await response(scope, receive, send)
        return
    await _gradio_app(scope, receive, send)


def launch():
    agents.start_background_load()
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "7860")),
    )


if __name__ == "__main__":
    launch()
