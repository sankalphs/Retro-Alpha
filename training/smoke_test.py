"""Smoke-test the Modal training image before launching full training."""

import modal

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.6.0-devel-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install("git", "build-essential", "curl", "libcurl4-openssl-dev")
    .pip_install("uv", "huggingface_hub", "hf_transfer")
    .run_commands(
        "uv pip install --system --no-cache "
        "    torch==2.7.1 triton>=3.3.0 "
        "    transformers==4.56.2 "
        "    datasets "
        "    trl "
        "    peft "
        "    accelerate "
        "    bitsandbytes "
        "    unsloth_zoo "
        "    'unsloth @ git+https://github.com/unslothai/unsloth'",
        "uv pip install --system --no-cache --no-build-isolation "
        "    mamba_ssm==2.2.5 causal_conv1d==1.5.2",
        "uv pip install --system --no-cache --no-deps 'torchao>=0.16.0'",
    )
)

app = modal.App("retro-alpha-smoke", image=image)

secrets = [modal.Secret.from_name("huggingface-secret")]


@app.function(gpu="A100-40GB", timeout=30 * 60, secrets=secrets)
def smoke():
    import os

    import torch
    from unsloth import FastLanguageModel

    print("CUDA available:", torch.cuda.is_available())
    print("CUDA devices:", torch.cuda.device_count())

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/NVIDIA-Nemotron-3-Nano-4B",
        max_seq_length=512,
        load_in_4bit=False,
        load_in_8bit=False,
        trust_remote_code=True,
        attn_implementation="eager",
    )
    print("Model loaded successfully")
    print("Tokenizer vocab size:", tokenizer.vocab_size)
    print("HF_TOKEN present:", bool(os.environ.get("HF_TOKEN")))
    return "Smoke test passed"


@app.local_entrypoint()
def main():
    print(smoke.remote())
