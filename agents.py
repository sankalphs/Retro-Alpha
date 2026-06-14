"""
Agent inference using either a Modal GPU endpoint or a local llama.cpp GGUF model.

If MODAL_INFERENCE_URL is set, all generation goes through the Modal endpoint
(GPU-accelerated, no local model load). Otherwise falls back to the local
llama.cpp background-load path for HF Spaces.

Loading is non-blocking: the model is loaded in a background thread
kicked off by the app's startup event. This lets uvicorn open the port
immediately (so HF Spaces' health check passes during a slow 2.84 GB
cold-start download) and surfaces a real "loading" status to the UI.

generate() is therefore non-blocking too:
  - "modal"   -> call remote Modal endpoint
  - "loaded"  -> call the real LLM
  - "mock"    -> return mock_generate(prompt)
  - otherwise -> return "" so the per-feature deterministic fallbacks
                 in chat_reply / generate_insight / parse_mentor_response
                 take over
"""

import json
import os
import re
import threading
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

ASSETS = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"]
PERSONAS = ["whale", "retail", "permabull"]

_DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "models"
_DEFAULT_MODEL_FILE = "NVIDIA-Nemotron-3-Nano-4B.Q4_K_M.gguf"
MODEL_PATH = os.getenv("MODEL_PATH") or str(_DEFAULT_MODEL_DIR / _DEFAULT_MODEL_FILE)

MODAL_URL = os.getenv("MODAL_INFERENCE_URL", "").rstrip("/")
USE_MODAL = bool(MODAL_URL)

_llm = None
_llm_status = "uninitialized"
_llm_error = ""
_load_started = False
_load_lock = threading.Lock()

if os.getenv("MOCK_LLM") == "1":
    _llm = "mock"
    _llm_status = "mock"
    _llm_error = "MOCK_LLM=1 (test mode)"

if USE_MODAL and _llm_status != "mock":
    _llm_status = "modal"
    _llm_error = ""


def llm_status() -> str:
    return _llm_status


def llm_error() -> str:
    return _llm_error


def _do_load() -> None:
    global _llm, _llm_status, _llm_error
    try:
        from llama_cpp import Llama
        mp = Path(MODEL_PATH)
        if not mp.exists():
            raise FileNotFoundError(
                f"Model file not found at '{mp}'. "
                f"Set MODEL_PATH or check the download."
            )
        size_gb = mp.stat().st_size / 1e9
        print(f"Loading LLM from {mp} ({size_gb:.2f} GB)...")
        _llm = Llama(
            model_path=str(mp),
            n_ctx=int(os.getenv("LLAMA_CTX", "2048")),
            n_threads=int(os.getenv("LLAMA_THREADS", "4")),
            verbose=False,
        )
        _llm_status = "loaded"
        _llm_error = ""
        print("LLM loaded successfully.")
    except Exception as e:
        _llm_error = f"{type(e).__name__}: {e}"
        print(f"Warning: could not load LLM: {_llm_error}. Using mock mode.")
        _llm = "mock"
        _llm_status = "error"


def start_background_load() -> None:
    global _load_started, _llm_status
    if _llm_status in ("mock", "modal"):
        return
    with _load_lock:
        if _load_started:
            return
        _load_started = True
        _llm_status = "loading"
    t = threading.Thread(target=_do_load, name="llm-loader", daemon=True)
    t.start()


def clean_text(text: str) -> str:
    text = text.strip()
    while "<think>" in text and "</think>" in text:
        s = text.find("<think>")
        e = text.find("</think>") + len("</think>")
        text = text[:s] + text[e:]
    return text.strip()


def generate(prompt: str, system: str = "", max_tokens: int = 256, temperature: float = 0.7) -> str:
    if _llm_status == "mock":
        return mock_generate(prompt, system)
    if USE_MODAL:
        return _remote_generate(prompt, system, max_tokens, temperature)
    if _llm_status != "loaded":
        return ""
    llm = _llm
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    for attempt, (mt, temp) in enumerate([(max_tokens, temperature), (max_tokens, 0.2)]):
        try:
            response = llm.create_chat_completion(
                messages=messages, max_tokens=mt, temperature=temp,
            )
        except Exception as e:
            print(f"Warning: LLM call failed (attempt {attempt}): {e}.")
            continue
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            continue
        if isinstance(content, str) and content.strip():
            return clean_text(content)
    print("Warning: LLM returned empty content after retries.")
    return ""


def _remote_generate(prompt: str, system: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
    import time

    try:
        import httpx
    except ImportError:
        print("httpx not installed. Install it for Modal inference: pip install httpx")
        return ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(2):
        try:
            resp = httpx.post(
                f"{MODAL_URL}/chat",
                json={"messages": messages, "max_tokens": max_tokens, "temperature": temperature},
                timeout=90.0,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str) and content.strip():
                return clean_text(content)
        except Exception as e:
            print(f"Modal inference attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                time.sleep(2)
    print("Warning: Modal inference returned empty content after retries.")
    return ""


def mock_generate(prompt: str, system: str = "") -> str:
    p = prompt.lower()
    s = system.lower()
    if "agent" in p and "whale" in p:
        return "agent: whale\naction: buy gov_bonds 0.10\nreason: safety first\nsentiment: cautious"
    if "agent" in p and "retail" in p:
        return "agent: retail\naction: sell nifty_it 0.10\nreason: panic selling\nsentiment: panic"
    if "agent" in p:
        return "agent: permabull\naction: buy crypto 0.10\nreason: buy the dip\nsentiment: bullish"
    if "roast" in p or "sharpe_ratio" in p:
        return "roast: diversify more\nsharpe_ratio: 0.5\nlesson: Sharpe ratio measures risk-adjusted return\nsuggestion: add bonds"
    if "insight" in p or "commentary" in p or "commentator" in s:
        return "insight: Markets are reacting to the headline. Watch for follow-through."
    if "headline" in p:
        return "headline: RBI holds rates steady\nimpact: cash:0 fd:0 gov_bonds:0 nifty_50:0 nifty_it:0 real_estate:0 crypto:0 gold:0\nduration: 1"
    return ""


def parse_agent_response(response: str, persona: str) -> Dict:
    response = clean_text(response)
    try:
        m_agent = re.search(r"agent:\s*(\w+)", response)
        agent = (m_agent.group(1).lower() if m_agent else persona) or persona
        m_action = re.search(r"action:\s*(buy|sell|hold)\s+(\w+)\s+([\d.%]+)", response)
        m_reason = re.search(r"reason:\s*(.+)", response)
        m_sent = re.search(r"sentiment:\s*(\w+)", response)
        if not m_action:
            return {"agent": agent, "actions": [{"asset": "cash", "action": "hold", "amount_pct": 0.0, "reason": "no action"}], "sentiment": "neutral"}
        return {
            "agent": agent,
            "actions": [{
                "asset": m_action.group(2),
                "action": m_action.group(1),
                "amount_pct": float(m_action.group(3)),
                "reason": (m_reason.group(1).strip() if m_reason else ""),
            }],
            "sentiment": (m_sent.group(1).lower() if m_sent else "neutral"),
        }
    except Exception as e:
        return {"agent": persona, "actions": [{"asset": "cash", "action": "hold", "amount_pct": 0.0, "reason": f"parse error: {e}"}], "sentiment": "neutral"}


def parse_news_response(response: str) -> Dict:
    response = clean_text(response)
    try:
        m_head = re.search(r"headline:\s*(.+)", response)
        m_imp = re.search(r"impact:\s*(.+?)(?:\nduration:|$)", response, re.DOTALL)
        m_dur = re.search(r"duration:\s*(\d+)", response)
        headline = m_head.group(1).strip() if m_head else "Markets mixed"
        impact = {}
        if m_imp:
            for token in m_imp.group(1).strip().split():
                if ":" in token:
                    k, v = token.split(":")
                    try:
                        impact[k] = float(v)
                    except ValueError:
                        pass
        for a in ASSETS:
            impact.setdefault(a, 0.0)
        duration = int(m_dur.group(1)) if m_dur else 1
        return {"headline": headline, "impact": impact, "duration_months": duration}
    except Exception as e:
        return {"headline": "Markets mixed", "impact": {a: 0.0 for a in ASSETS}, "duration_months": 1, "error": str(e)}


def decide_agent(persona: str, state: Dict) -> Dict:
    system = (
        f"You are an NPC trader in an Indian stock-market game. "
        f"Output the {persona}'s decision in EXACT format:\n"
        f"agent: {persona}\naction: <buy|sell|hold> <asset> <amount_pct>\n"
        f"reason: <short reason>\nsentiment: <bullish|bearish|neutral|panic|cautious>"
    )
    compact = {
        "month": state.get("month"),
        "year": state.get("year"),
        "cash": state.get("cash"),
        "total_value": state.get("total_value"),
    }
    prompt = f"State: {json.dumps(compact)}. Persona: {persona}. Decide."
    response = generate(prompt, system=system, max_tokens=150, temperature=0.6)
    return parse_agent_response(response, persona)


def generate_news(event: Dict) -> Dict:
    headline = event.get("headline", "Markets trade in tight range")
    regime = event.get("regime", "stagnation")
    impact = event.get("impact", {})
    for a in ASSETS:
        impact.setdefault(a, 0.0)
    return {
        "headline": headline,
        "regime": regime,
        "impact": {k: float(v) for k, v in impact.items()},
        "duration_months": int(event.get("duration_months", 1)),
        "year": int(event.get("year", 0)),
        "month": int(event.get("month", 0)),
    }


def generate_insight(event: Dict, state_snapshot: Dict) -> str:
    if not event:
        return "Markets are quiet. Use the time to review your allocation."

    pnl = float(state_snapshot.get("unrealized_pnl", 0.0))
    cash = float(state_snapshot.get("cash", 0.0))
    total = float(state_snapshot.get("total_value", 0.0))
    cash_pct = (cash / total * 100.0) if total else 0.0
    regime = str(event.get("regime", "stagnation"))
    headline = str(event.get("headline", ""))

    system = (
        "You are a sharp Indian markets commentator. Given a market event "
        "and a player's portfolio snapshot, output ONE sentence (under 140 chars) "
        "of actionable insight. No preamble. Start with the verb."
    )
    prompt = (
        f"Event: {headline} (regime: {regime}). "
        f"Player P&L ₹{pnl:,.0f}, cash {cash_pct:.0f}%, total ₹{total:,.0f}. "
        f"One actionable sentence."
    )
    try:
        text = generate(prompt, system=system, max_tokens=80, temperature=0.4).strip()
    except Exception:
        text = ""
    if not text:
        if pnl < -50_000:
            text = f"Cut losers in {regime.replace('_', ' ')} regimes and rotate into defensives."
        elif pnl > 50_000:
            text = f"Book partial profits; {regime.replace('_', ' ')} trends rarely last."
        elif cash_pct > 60:
            text = "Heavy cash drag. Deploy into bonds or Nifty on dips."
        else:
            text = f"Hold the line through this {regime.replace('_', ' ')} phase."
    return text[:200]


def chat_reply(user_message: str, state_snapshot: Dict) -> str:
    pnl = float(state_snapshot.get("unrealized_pnl", 0.0))
    cash = float(state_snapshot.get("cash", 0.0))
    total = float(state_snapshot.get("total_value", 0.0))
    positions = state_snapshot.get("positions", [])
    pos_lines = ", ".join(
        f"{p['asset']} {p['qty']:.2f} @ ₹{p['price']:.0f}" for p in positions[:8]
    ) or "no positions"

    system = (
        "You are Retro Alpha, a sharp Indian markets assistant in a 1990s "
        "stock-trading game. Be concise, witty, and grounded in the player's "
        "actual positions. 2-3 short sentences max. No fluff."
    )
    prompt = (
        f"Portfolio: total ₹{total:,.0f}, cash ₹{cash:,.0f}, "
        f"unrealized P&L ₹{pnl:,.0f}. Positions: {pos_lines}.\n"
        f"Player: {user_message}\nReply in 2-3 short sentences."
    )
    try:
        text = generate(prompt, system=system, max_tokens=140, temperature=0.5).strip()
    except Exception:
        text = ""
    if not text:
        if "buy" in user_message.lower() or "should i" in user_message.lower():
            text = f"With cash at ₹{cash:,.0f} and P&L ₹{pnl:,.0f}, I'd wait for a confirmed trend before adding. Check the chart for support levels."
        elif "sell" in user_message.lower():
            text = "Selling into strength is a discipline. If your position is >20% of portfolio, trim 10% and rebalance."
        elif pnl < 0:
            text = f"You're down ₹{abs(pnl):,.0f}. Don't add to losers. Rotate into bonds or gold until the regime clarifies."
        else:
            text = f"Up ₹{pnl:,.0f} — not bad. Lock in some gains into FDs so the win isn't just on paper."
    return text[:500]


def all_agents_decide(state: Dict) -> List[Dict]:
    return [decide_agent(p, state) for p in PERSONAS]
