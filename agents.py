"""
Agent inference using a local llama.cpp GGUF model.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

ASSETS = ["cash", "fd", "gov_bonds", "nifty_50", "nifty_it", "real_estate", "crypto", "gold"]
PERSONAS = ["whale", "retail", "permabull"]

# Default model path; override via MODEL_PATH env var
MODEL_PATH = os.getenv("MODEL_PATH", "models/retro-alpha-nemotron-q4_k_m.gguf")

_llm = None

# Allow forcing mock mode for fast local testing / CI
if os.getenv("MOCK_LLM") == "1":
    _llm = "mock"


def get_llm():
    global _llm
    if _llm is None:
        try:
            from llama_cpp import Llama
            if not Path(MODEL_PATH).exists():
                raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
            _llm = Llama(
                model_path=MODEL_PATH,
                n_ctx=2048,
                n_threads=int(os.getenv("LLAMA_THREADS", "4")),
                verbose=False,
            )
        except Exception as e:
            print(f"Warning: could not load LLM: {e}. Using mock mode.")
            _llm = "mock"
    return _llm


def clean_text(text: str) -> str:
    text = text.strip()
    while "<think>" in text and "</think>" in text:
        s = text.find("<think>")
        e = text.find("</think>") + len("</think>")
        text = text[:s] + text[e:]
    return text.strip()


def generate(prompt: str, system: str = "", max_tokens: int = 256, temperature: float = 0.7) -> str:
    llm = get_llm()
    if llm == "mock":
        return mock_generate(prompt, system)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return clean_text(response["choices"][0]["message"]["content"])


def mock_generate(prompt: str, system: str = "") -> str:
    """Deterministic fallback when no model is loaded."""
    if "agent" in prompt.lower() and "whale" in prompt.lower():
        return "agent: whale\naction: buy gov_bonds 0.10\nreason: safety first\nsentiment: cautious"
    if "agent" in prompt.lower() and "retail" in prompt.lower():
        return "agent: retail\naction: sell nifty_it 0.10\nreason: panic selling\nsentiment: panic"
    if "agent" in prompt.lower():
        return "agent: permabull\naction: buy crypto 0.10\nreason: buy the dip\nsentiment: bullish"
    if "headline" in prompt.lower():
        return "headline: RBI holds rates steady\nimpact: cash:0 fd:0 gov_bonds:0 nifty_50:0 nifty_it:0 real_estate:0 crypto:0 gold:0\nduration: 1"
    if "roast" in prompt.lower():
        return "roast: diversify more\nsharpe_ratio: 0.5\nlesson: Sharpe ratio measures risk-adjusted return\nsuggestion: add bonds"
    return "error: format only"


def parse_agent_response(response: str, persona: str) -> Dict:
    response = clean_text(response)
    try:
        agent = re.search(r"agent:\s*(\w+)", response).group(1).lower()
        action_match = re.search(r"action:\s*(buy|sell|hold)\s+(\w+)\s+([\d.%]+)", response)
        reason = re.search(r"reason:\s*(.+)", response).group(1).strip()
        sentiment = re.search(r"sentiment:\s*(\w+)", response).group(1).lower()
        return {
            "agent": agent or persona,
            "actions": [{"asset": action_match.group(2), "action": action_match.group(1), "amount_pct": float(action_match.group(3)), "reason": reason}],
            "sentiment": sentiment,
        }
    except Exception as e:
        return {"agent": persona, "actions": [{"asset": "cash", "action": "hold", "amount_pct": 0.0, "reason": f"parse error: {e}"}], "sentiment": "neutral"}


def parse_news_response(response: str) -> Dict:
    response = clean_text(response)
    try:
        headline = re.search(r"headline:\s*(.+)", response).group(1).strip()
        impact_match = re.search(r"impact:\s*(.+?)(?:\nduration:|$)", response, re.DOTALL)
        duration = int(re.search(r"duration:\s*(\d+)", response).group(1))
        impact = {}
        for token in impact_match.group(1).strip().split():
            if ":" in token:
                k, v = token.split(":")
                impact[k] = float(v)
        for a in ASSETS:
            impact.setdefault(a, 0.0)
        return {"headline": headline, "impact": impact, "duration_months": duration}
    except Exception as e:
        return {"headline": "Markets mixed", "impact": {a: 0.0 for a in ASSETS}, "duration_months": 1, "error": str(e)}


def decide_agent(persona: str, state: Dict) -> Dict:
    system = f"You are an NPC behavior designer for an educational Indian stock-market video game. Output the {persona}'s decision in exact format:\nagent: <persona>\naction: <buy|sell|hold> <asset> <amount_pct>\nreason: <short reason>\nsentiment: <bullish|bearish|neutral|panic|cautious>"
    prompt = f"Market state: {json.dumps(state)}\nPersona: {persona}"
    response = generate(prompt, system=system, max_tokens=200)
    return parse_agent_response(response, persona)


def generate_news(regime: str) -> Dict:
    system = "You are a scenario writer for an Indian stock-market simulation game. Output exact format:\nheadline: <short headline>\nimpact: cash:<n> fd:<n> gov_bonds:<n> nifty_50:<n> nifty_it:<n> real_estate:<n> crypto:<n> gold:<n>\nduration: <months>"
    prompt = f"Generate a fictional Indian financial headline for regime: {regime.replace('_', ' ').title()}."
    response = generate(prompt, system=system, max_tokens=200)
    return parse_news_response(response)


def all_agents_decide(state: Dict) -> List[Dict]:
    return [decide_agent(p, state) for p in PERSONAS]
