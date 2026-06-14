FROM python:3.11-slim

WORKDIR /app

# System dependencies:
#   - git, curl                      : hf_hub_download + health checks
#   - cmake, build-essential         : compile llama-cpp-python from source
#                                      (avoids the musl/glibc mismatch from
#                                      prebuilt wheels on Debian base image)
#   - libgomp1, libgfortran5         : OpenMP + Fortran runtimes required by
#                                      the compiled libllama.so at runtime
# Cache bust: 2026-06-14-v4
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    cmake \
    build-essential \
    libgomp1 \
    libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps, forcing llama-cpp-python to compile from source
COPY requirements.txt .
RUN pip install --no-cache-dir --no-binary llama-cpp-python -r requirements.txt

# Copy application code
COPY . .

# Pre-create models directory
RUN mkdir -p /app/models

EXPOSE 7860

CMD ["python", "app.py"]
