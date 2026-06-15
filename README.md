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
---

# Retro Alpha

A 90s CRT-style Indian stock-market survival game (1994-2004), powered by a fine-tuned NVIDIA Nemotron-3-Nano 4B model. Built for the Build Small Hackathon.

## How to Play
- **Goal:** Turn ₹10,00,000 into ₹20,00,000 over 10 years (120 months)
- **1. Review:** Check the Market Watch for asset prices and trends
- **2. Trade:** Buy/Sell any asset as a % of your portfolio using the Order Pad
- **3. Advance:** Press **Advance Month** to trigger real historical events & market moves
- Click any asset in the Market Watch to view its price chart
- Ask the AI Advisor about your portfolio or strategy
- Get a Year-End Mentor Review for a sarcastic roast & investment lesson

## Real Historical Events
Asian Financial Crisis, Pokhran-II nuclear tests, Dot-com bubble, 9/11, 2004 Indian elections, and more.

## Tech Stack
- **Frontend:** Custom CRT terminal UI (vanilla HTML/CSS/JS), Gradio Blocks
- **Backend:** Python, Gradio (FastAPI under the hood)
- **Model:** Fine-tuned NVIDIA Nemotron-3-Nano 4B (Q4_K_M GGUF)
- **Inference:** Modal GPU cloud endpoint (deterministic fallbacks when offline)
- **Badges:** Off-Brand (custom UI), Well-Tuned (fine-tuned model), Nemotron

## Running Locally
```bash
pip install -r requirements.txt
MOCK_LLM=1 python app.py
```

For LLM-powered features, set `MODAL_INFERENCE_URL` or `HF_API_URL` + `HF_TOKEN`.
