FROM python:3.11-slim

WORKDIR /app

# Install git for hf_hub_download and curl for health checks
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps (uses prebuilt llama-cpp-python wheel)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application code
COPY . .

# Pre-create models directory
RUN mkdir -p /app/models

EXPOSE 7860

CMD ["python", "app.py"]
