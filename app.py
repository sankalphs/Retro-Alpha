"""
Retro Alpha — FastAPI backend.
Serves the static frontend and the LLM-backed endpoints (chat, mentor,
insight). The game itself runs 100% in the browser (see static/engine.js);
the server holds NO per-user state. This guarantees every browser tab has
its own independent game.
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import agents
import download_model

app = FastAPI(title="Retro Alpha")
ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

# Ensure the GGUF is on disk, then eagerly load it into RAM so
# /api/health reflects the REAL status (not "uninitialized") as soon
# as the container is up. Lazy-loading would race the first health
# check and surface a generic "model not loaded" with no error reason.
try:
    agents.MODEL_PATH = download_model.download()
    print(f"Model path: {agents.MODEL_PATH}")
    print("Eagerly loading LLM into memory (this may take ~10-60s)...")
    _ = agents.get_llm()  # triggers Llama(...) load; sets status + error
    err = agents.llm_error()
    print(f"LLM status: {agents.llm_status()} ({err or 'ok'})")
except Exception as e:
    print(f"Startup LLM init failed: {e}")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def homepage():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
def health() -> JSONResponse:
    from pathlib import Path as _Path
    mp = _Path(str(agents.MODEL_PATH))
    return JSONResponse({
        "status": "ok",
        "llm": agents.llm_status(),
        "llm_error": agents.llm_error(),
        "model_path": str(agents.MODEL_PATH),
        "model_exists": mp.exists(),
        "model_size_gb": round(mp.stat().st_size / 1e9, 2) if mp.exists() else 0,
    })


@app.post("/api/chat")
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


@app.post("/api/insight")
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


@app.post("/api/mentor")
async def mentor_review(request: Request) -> JSONResponse:
    data = await request.json()
    summary = data.get("summary") or {}
    import mentor as _mentor
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "7860")))
