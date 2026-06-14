"""
Modal LLM inference endpoint for Retro Alpha.
Serves the fine-tuned Nemotron-3 GGUF on A10G GPU for fast inference.
Kept warm (scaledown_window=3600) to avoid cold starts.

Usage:
    modal serve modal_app.py       # local tunnel for testing
    modal deploy modal_app.py      # deploy to Modal cloud

After deployment, set MODAL_INFERENCE_URL to the returned URL in .env.
"""

import os

import modal
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

MODEL_REPO = os.getenv("MODEL_REPO", "sankalphs/retro-alpha-nemotron-gguf")
MODEL_FILE = os.getenv("MODEL_FILE", "NVIDIA-Nemotron-3-Nano-4B.Q4_K_M.gguf")
MODEL_DIR = "/models"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "curl", "cmake", "build-essential", "libgomp1", "libgfortran5")
    .pip_install(
        "fastapi",
        "llama-cpp-python",
        "python-dotenv",
        "huggingface_hub",
    )
    .env({
        "CMAKE_ARGS": "-DGGML_CUDA=on",
        "FORCE_CMAKE": "1",
    })
    .run_commands("mkdir -p " + MODEL_DIR)
)

app = modal.App("retro-alpha-inference", image=image)

hf_secret = modal.Secret.from_name("huggingface-secret")


@app.cls(gpu="A10G", scaledown_window=3600, secrets=[hf_secret])
class Nemotron:
    @modal.enter()
    def load(self):
        import time
        from pathlib import Path

        local_path = Path(MODEL_DIR) / MODEL_FILE

        if local_path.exists() and local_path.stat().st_size > 100_000_000:
            size_gb = local_path.stat().st_size / 1e9
            print(f"Model cached: {local_path} ({size_gb:.2f} GB)")
        else:
            from huggingface_hub import hf_hub_download
            for attempt in range(1, 4):
                try:
                    print(f"Downloading {MODEL_FILE} from {MODEL_REPO} (attempt {attempt}/3)...")
                    hf_hub_download(
                        repo_id=MODEL_REPO,
                        filename=MODEL_FILE,
                        local_dir=MODEL_DIR,
                        local_dir_use_symlinks=False,
                    )
                    break
                except Exception as e:
                    print(f"Download attempt {attempt} failed: {e}")
                    if attempt < 3:
                        time.sleep(2 ** attempt)

        from llama_cpp import Llama
        n_gpu = int(os.getenv("LLAMA_GPU_LAYERS", "-1"))
        print(f"Loading {local_path} (n_gpu_layers={n_gpu}, n_ctx=2048)...")
        self.llm = Llama(
            model_path=str(local_path),
            n_ctx=int(os.getenv("LLAMA_CTX", "2048")),
            n_gpu_layers=n_gpu,
            verbose=False,
        )
        print("Model loaded.")

    def _build_app(self):
        web_app = FastAPI()

        @web_app.post("/chat")
        async def chat(request: Request):
            data = await request.json()
            messages = data.get("messages", [])
            max_tokens = int(data.get("max_tokens", 256))
            temperature = float(data.get("temperature", 0.7))

            if not messages:
                return JSONResponse({"error": "No messages provided"}, status_code=400)

            result = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return result

        @web_app.get("/health")
        async def health():
            from pathlib import Path

            local_path = Path(MODEL_DIR) / MODEL_FILE
            return {
                "status": "ok" if local_path.exists() else "model_missing",
                "model_path": str(local_path),
                "model_size_gb": round(local_path.stat().st_size / 1e9, 2) if local_path.exists() else 0,
            }

        return web_app

    @modal.asgi_app()
    def fastapi_app(self):
        return self._build_app()
