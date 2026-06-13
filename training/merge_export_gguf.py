"""
Merge LoRA adapter into base model and export to GGUF for llama.cpp inference.

Usage:
    modal run training.merge_export_gguf
"""

import os

import modal

app = modal.App("retro-alpha-merge-export")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "build-essential", "cmake")
    .pip_install(
        "torch==2.3.0",
        "transformers==4.41.0",
        "peft==0.11.0",
        "huggingface_hub==0.23.0",
        "gguf",
    )
    .run_commands(
        "git clone https://github.com/ggerganov/llama.cpp.git /tmp/llama.cpp",
        "cd /tmp/llama.cpp && cmake -B build . && cmake --build build --config Release -j4",
    )
)

secrets = [modal.Secret.from_name("hf-token", required=False)]


@app.function(
    image=image,
    gpu=modal.gpu.A100(size="40GB"),
    timeout=60 * 60 * 3,
    secrets=secrets,
)
def merge_and_export(
    base_model: str = "nvidia/Nemotron-3-Nano-4B-Chat",
    lora_repo: str = "build-small-hackathon/retro-alpha-nemotron-lora",
    output_repo: str = "build-small-hackathon/retro-alpha-nemotron-gguf",
    quantization: str = "Q4_K_M",
):
    import torch
    from huggingface_hub import HfApi, login
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        login(token=hf_token)

    print(f"Loading base model: {base_model}")
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    print(f"Loading LoRA adapter: {lora_repo}")
    model = PeftModel.from_pretrained(base, lora_repo)

    print("Merging adapter into base model...")
    merged = model.merge_and_unload()

    merged_dir = "/tmp/retro-alpha-merged"
    print(f"Saving merged model to {merged_dir}")
    merged.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)

    # Convert to GGUF
    gguf_dir = "/tmp/retro-alpha-gguf"
    os.makedirs(gguf_dir, exist_ok=True)
    gguf_path = f"{gguf_dir}/retro-alpha-nemotron-{quantization.lower()}.gguf"

    convert_script = "/tmp/llama.cpp/convert_hf_to_gguf.py"
    print(f"Converting to GGUF: {gguf_path}")
    os.system(
        f"python {convert_script} {merged_dir} --outfile {gguf_path} --outtype {quantization}"
    )

    # Push to HF
    if hf_token:
        print(f"Pushing GGUF to {output_repo}")
        api = HfApi(token=hf_token)
        api.create_repo(repo_id=output_repo, exist_ok=True, repo_type="model")
        api.upload_file(path_or_fileobj=gguf_path, path_in_repo=f"retro-alpha-nemotron-{quantization.lower()}.gguf", repo_id=output_repo)

    return f"GGUF exported to {output_repo}/retro-alpha-nemotron-{quantization.lower()}.gguf"


@app.local_entrypoint()
def main():
    result = merge_and_export.remote()
    print(result)
