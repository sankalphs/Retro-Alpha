# Retro Alpha — Build Log

## Project Goal
Build "Retro Alpha", a 90s CRT trading terminal game for the Hugging Face Build Small Hackathon. The game runs a multi-agent Indian financial market simulation using a fine-tuned NVIDIA Nemotron-3-Nano-4B model served locally via llama.cpp. Target all 6 bonus badges: Off the Grid, Well-Tuned, Off-Brand, Llama Champion, Sharing is Caring, Field Notes.

## Asset Universe (India Edition)
- Cash (INR)
- Bank Fixed Deposit (FD)
- Government Bonds (G-Secs)
- Nifty 50
- Nifty IT
- Real Estate (REITs/index)
- Crypto (BTC/ETH)
- Gold

## Personas
- **Institutional Whale**: slow, bonds + Nifty 50
- **Retail Day Trader**: panic sells, chases hype
- **Tech Permabull**: always leveraged into IT/crypto

## Tech Stack
- Frontend: custom HTML/CSS/JS served via `gradio.Server`
- Backend: Python simulation engine
- Inference: `llama-cpp-python` with GGUF Q4_K_M
- Fine-tuning: Modal A100 40GB with LoRA
- Data generation: zenmux API (`moonshotai/kimi-k2.7-code-free`) with 20 concurrent calls

## Build Phases
1. Project setup + synthetic dataset generation
2. Dataset validation + push to HF
3. Modal LoRA fine-tuning
4. GGUF conversion + model publish
5. Gradio Server backend
6. CRT terminal frontend
7. Integration + HF Space deployment
8. CI/CD pipeline (GitHub Actions)
9. Field notes + demo

---

## Entries

### 2026-06-13 — Phase 1 Start
- Initialized repository structure.
- Created `.gitignore`, `.env.example`, `requirements.txt`, `config/assets.json`, schemas, and generation scripts.
- Created `.env` with zenmux API credentials (not committed due to `.gitignore`).
- User note: HF Space redeployment rate limit hit; will defer Space pushes until later.
- Iterated prompt engineering to handle API quirks: model requires game/NPC framing to avoid empty financial-advice refusals; compact single-line JSON reduces truncation; markdown fences stripped in post-processing.
- Mini audit test passed: 20/20 rows generated and JSON-parseable with 5 concurrent calls.
- Tested alternative API (tokenrouter / MiniMax-M3): discovered a hard output-token cap (~285 tokens) that truncates mentor and news JSON. Switched back to zenmux / kimi-k2.7-code-free because it completes longer JSON reliably.
- Reduced dataset target from 2,500 to 1,500 high-quality rows to respect time and API reliability; this is sufficient for LoRA fine-tuning.
- Added chunked incremental saving (every 100 rows) so progress survives timeouts.
- Investigated tokenrouter / MiniMax-M3 thoroughly. The model emits mandatory `<think>` blocks, making strict JSON unreliable. Switched dataset format to simple structured text (key: value lines), which MiniMax-M3 handles much better.
- Mini audit with text format: non-empty responses are coherent, but ~50% of calls return only thinking tags (empty after cleaning). Strategy: generate ~3,000 rows and filter to ~1,500 valid, parseable rows.
- Parser updated to handle decimals and percentages, angle brackets around placeholders.
- Generated 3,000 rows with MiniMax-M3 text format; validated down to 1,269 clean rows.
- Generated 500 extra mentor rows; 177 valid. Final dataset: 1,446 rows.
- Final distribution: ~730 agent, ~281 news, ~255 mentor, ~180 guardrail.
- Next: push dataset to HF and run Modal LoRA fine-tuning.
