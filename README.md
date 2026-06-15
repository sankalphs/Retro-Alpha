---
title: Retro Alpha
emoji: 📺
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
tags:
  - thousand-token-wood
  - off-brand
  - well-tuned
  - nemotron
  - build-small-hackathon
---

# Retro Alpha

**A 90s CRT-style Indian stock market survival game (1994–2004), powered by a fine-tuned NVIDIA Nemotron-3-Nano 4B model.**

Built for the [🤗 Build Small Hackathon](https://huggingface.co/build-small-hackathon).

👉 **[Play the game on HF Spaces](https://huggingface.co/spaces/sankalphs/retro-alpha)**

---

## 🎮 How to Play

| Step | Action |
|------|--------|
| **Goal** | Turn ₹10,00,000 into ₹20,00,000 over 10 years (120 months) |
| **Review** | Check the Market Watch for asset prices & trends |
| **Trade** | Buy/Sell any asset as a % of your portfolio using the Order Pad |
| **Advance** | Press Advance Month to trigger real historical events & market moves |
| **Analyze** | Ask the AI Advisor about your portfolio or strategy |
| **Review** | Get a Year-End Mentor Review for a sarcastic roast & investment lesson |

### Historical Events
Asian Financial Crisis, Pokhran-II nuclear tests, Dot-com bubble, 9/11, 2004 Indian elections, and more — all influencing asset prices based on real historical data.

---

## 🏆 Badges Earned

| Badge | How |
|-------|-----|
| **Off-Brand** | Custom CRT terminal UI built from scratch (no Gradio default) |
| **Well-Tuned** | Fine-tuned Nemotron-3-Nano 4B on 1,500+ synthetic market scenarios |
| **Nemotron** | Uses fine-tuned NVIDIA Nemotron-3-Nano-4B (Q4_K_M GGUF) |
| **Off the Grid** | Fully self-contained Docker Space with on-device inference |
| **Sharing is Caring** | Infrastructure-as-code scripts open-sourced on GitHub |
| **Field Notes** | Detailed build log & methodology documented |

---

## 🧱 Tech Stack

```
Frontend   → Custom CRT terminal UI (vanilla HTML/CSS/JS) served via ASGI
Backend    → Python simulation engine + Gradio API
Model      → Fine-tuned NVIDIA Nemotron-3-Nano 4B (Q4_K_M GGUF)
Inference  → Modal GPU cloud endpoint (A10G) with deterministic fallbacks
Data       → 1,500+ synthetic Indian market scenarios via zenmux API
CI/CD      → GitHub Actions → HF Spaces auto-deploy
```

---

## 🚀 Running Locally

```bash
pip install -r requirements.txt
MOCK_LLM=1 python app.py
```

For LLM-powered features, set one of:
- `MODAL_INFERENCE_URL` — Modal cloud endpoint
- `HF_API_URL` + `HF_TOKEN` — Hugging Face Inference API

---

## 📁 Project Structure

```
├── app.py              # Gradio app entrypoint (ASGI)
├── agents.py           # LLM inference wrapper
├── engine.py           # Market simulation engine
├── events.py           # Historical event triggers
├── mentor.py           # AI mentor review generator
├── modal_app.py        # Modal GPU inference endpoint
├── download_model.py   # GGUF model downloader
├── Dockerfile          # HF Space container
├── requirements.txt    # Runtime dependencies
├── requirements-train.txt  # Training dependencies
├── config/
│   └── assets.json     # Asset definitions
├── static/             # Frontend (CSS, JS, HTML)
├── schemas/            # JSON schemas for dataset validation
├── data/               # Training datasets
├── scripts/            # Dataset generation & validation
├── training/           # Modal LoRA fine-tuning scripts
└── tests/              # Test suite
```

---

## 🧠 Model

The game uses a LoRA fine-tune of **NVIDIA Nemotron-3-Nano-4B** on a custom dataset of 1,500+ Indian market scenarios covering:

- **Agent decisions** (730 examples) — institutional, retail, and tech-permabull personas
- **News impacts** (281 examples) — historical event market reactions
- **Mentor reviews** (255 examples) — year-end portfolio roasts with Sharpe ratios
- **Guardrails** (180 examples) — safety and formatting guidelines

Fine-tuned on Modal A100 40GB → exported as GGUF Q4_K_M for efficient inference.

---

## 📄 License

MIT
