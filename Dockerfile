FROM python:3.11-slim

WORKDIR /app

# System dependencies:
#   - git, curl                 : hf_hub_download + health checks
#   - libgomp1, libgfortran5    : OpenMP + Fortran runtimes required by
#                                 the prebuilt llama-cpp-python wheel's
#                                 libllama.so (NOT in the slim base image;
#                                 without these you get
#                                 "Failed to load shared library ... libgomp.so.1")
#   - cmake, build-essential     : safety net so pip can build llama-cpp-python
#                                 from source if the prebuilt wheel is ever
#                                 unavailable for this Python version
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    libgomp1 \
    libgfortran5 \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps (prefer prebuilt llama-cpp-python wheel)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application code
COPY . .

# Pre-create models directory
RUN mkdir -p /app/models

EXPOSE 7860

CMD ["python", "app.py"]
