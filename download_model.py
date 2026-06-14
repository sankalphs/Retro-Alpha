"""Download the fine-tuned GGUF model from Hugging Face."""

import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

load_dotenv()

MODEL_REPO = os.getenv("MODEL_REPO", "sankalphs/retro-alpha-nemotron-gguf")
MODEL_FILE = os.getenv("MODEL_FILE", "NVIDIA-Nemotron-3-Nano-4B.Q4_K_M.gguf")
MODEL_DIR = Path(__file__).resolve().parent / "models"


def download() -> str:
    MODEL_DIR.mkdir(exist_ok=True)
    local_path = MODEL_DIR / MODEL_FILE
    if local_path.exists():
        return str(local_path)

    print(f"Downloading {MODEL_FILE} from {MODEL_REPO}...")
    path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        local_dir=str(MODEL_DIR),
        local_dir_use_symlinks=False,
        token=os.getenv("HF_TOKEN"),
    )
    return path


if __name__ == "__main__":
    print(download())
