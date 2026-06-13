FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for llama.cpp
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Pre-create models directory
RUN mkdir -p /app/models

EXPOSE 7860

CMD ["python", "app.py"]
