"""Download the fine-tuned GGUF model from Hugging Face.

Robust download: returns the expected local path even on failure so the
rest of the app can report a clear "model not found" error instead of
crashing at startup. Tries with the token first, then anonymously
(works for public repos)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MODEL_REPO = os.getenv("MODEL_REPO", "sankalphs/retro-alpha-nemotron-gguf")
MODEL_FILE = os.getenv("MODEL_FILE", "NVIDIA-Nemotron-3-Nano-4B.Q4_K_M.gguf")
MODEL_DIR = Path(__file__).resolve().parent / "models"


def _local_path() -> Path:
    return MODEL_DIR / MODEL_FILE


def download() -> str:
    """Ensure the GGUF model is available locally. Returns the local path
    as a string. Never raises — returns the expected path even on
    failure so callers can surface a precise error to the user."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    local = _local_path()

    if local.exists() and local.stat().st_size > 100_000_000:
        size_gb = local.stat().st_size / 1e9
        print(f"Model already present: {local} ({size_gb:.2f} GB)")
        return str(local)

    token = os.getenv("HF_TOKEN")
    # Try with token first (for private repos), then anonymously (public).
    for attempt_token, label in [(token, "with token"), (None, "anonymously")]:
        if attempt_token == "":
            attempt_token = None
        try:
            print(f"Downloading {MODEL_FILE} from {MODEL_REPO} ({label})...")
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(
                repo_id=MODEL_REPO,
                filename=MODEL_FILE,
                local_dir=str(MODEL_DIR),
                local_dir_use_symlinks=False,
                token=attempt_token,
            )
            print(f"Download complete: {path}")
            return str(path)
        except Exception as e:
            print(f"Download attempt failed ({label}): {type(e).__name__}: {e}")
            if attempt_token is None:
                break  # don't retry anonymous again

    # Download failed; return the expected path so the app can report
    # a clear "model not found" error rather than crashing.
    print(f"Model download failed. Expected at: {local}")
    return str(local)


if __name__ == "__main__":
    print(download())
