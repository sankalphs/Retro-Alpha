"""
Merge LoRA adapter into base model and export to GGUF for llama.cpp inference.

Usage:
    modal run -m training.merge_export_gguf

Based on Unsloth's GGUF export guide:
  https://unsloth.ai/docs/basics/inference-and-deployment/saving-to-gguf
"""

import os

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

app = modal.App("retro-alpha-merge-export", image=image)

secrets = [modal.Secret.from_name("huggingface-secret")]


@app.function(
    gpu="A100-40GB",
    timeout=60 * 60 * 4,
    secrets=secrets,
)
def merge_and_export(
    base_model: str = "unsloth/NVIDIA-Nemotron-3-Nano-4B",
    lora_repo: str = "sankalphs/retro-alpha-nemotron-lora",
    output_repo: str = "sankalphs/retro-alpha-nemotron-gguf",
    quantization: str = "q4_k_m",
):
    from huggingface_hub import HfApi, login
    from unsloth import FastLanguageModel

    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        login(token=hf_token)

    print(f"Loading base model + LoRA: {base_model} + {lora_repo}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=lora_repo,
        max_seq_length=2048,
        load_in_4bit=False,
        load_in_8bit=False,
        full_finetuning=False,
        trust_remote_code=True,
        attn_implementation="eager",
    )

    # Unsloth merges the LoRA adapter on the fly when loading from a LoRA repo,
    # but we still call for_inference to ensure inference mode is enabled.
    FastLanguageModel.for_inference(model)

    print(f"Pushing merged GGUF ({quantization}) to {output_repo}")
    try:
        model.push_to_hub_gguf(
            output_repo,
            tokenizer,
            quantization_method=quantization,
            token=hf_token,
        )
    except Exception as e:
        print(f"Could not push to {output_repo}: {e}")
        api = HfApi(token=hf_token)
        me = api.whoami()["name"]
        fallback = f"{me}/retro-alpha-nemotron-gguf"
        print(f"Trying fallback {fallback}")
        model.push_to_hub_gguf(
            fallback,
            tokenizer,
            quantization_method=quantization,
            token=hf_token,
        )
        output_repo = fallback

    return f"GGUF exported to {output_repo} with quantization {quantization}"


@app.local_entrypoint()
def main():
    result = merge_and_export.remote()
    print(result)
