FROM python:3.11-slim

WORKDIR /app

# Cache bust: 2026-06-14-v5
# System dependencies: git, curl for hf_hub_download + health checks
# llm inference is handled by Modal GPU (set MODAL_INFERENCE_URL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (no llama-cpp-python, inference is on Modal)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 7860

CMD ["python", "app.py"]
