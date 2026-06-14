"""
Modal fine-tuning script for Retro Alpha.
Fine-tunes unsloth/NVIDIA-Nemotron-3-Nano-4B with 16-bit LoRA on the Retro Alpha dataset.

Usage:
    modal run -m training.modal_train

Based on Unsloth's Nemotron 3 fine-tuning guide:
  https://docs.unsloth.ai/models/nemotron-3
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
        # Pin versions matching Unsloth's Nemotron 3 notebook.
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
        # Mamba / causal-conv1d are required by Nemotron-H architecture.
        "uv pip install --system --no-cache --no-build-isolation "
        "    mamba_ssm==2.2.5 causal_conv1d==1.5.2",
        # Optional torchao dependency used by Unsloth.
        "uv pip install --system --no-cache --no-deps 'torchao>=0.16.0'",
    )
)

app = modal.App("retro-alpha-finetune", image=image)

secrets = [modal.Secret.from_name("huggingface-secret")]


@app.function(
    gpu="A100-40GB",
    timeout=60 * 60 * 6,  # 6 hours
    secrets=secrets,
)
def train(
    base_model: str = "unsloth/NVIDIA-Nemotron-3-Nano-4B",
    dataset_repo: str = "sankalphs/retro-alpha-dataset",
    output_repo: str = "sankalphs/retro-alpha-nemotron-lora",
    num_epochs: int = 3,
    per_device_batch_size: int = 4,
    gradient_accumulation_steps: int = 4,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    max_seq_length: int = 1024,
):
    import torch
    from datasets import load_dataset
    from transformers import TrainingArguments
    from trl import SFTTrainer
    from unsloth import FastLanguageModel

    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        from huggingface_hub import login
        login(token=hf_token)

    print(f"Loading base model: {base_model}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=max_seq_length,
        load_in_4bit=False,   # user asked for non-quantized fine-tuning
        load_in_8bit=False,
        full_finetuning=False,
        trust_remote_code=True,
        attn_implementation="eager",
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
            "in_proj", "out_proj",
        ],
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    model.print_trainable_parameters()

    print(f"Loading dataset: {dataset_repo}")
    dataset = load_dataset(dataset_repo, split="train")

    def format_messages(examples):
        convos = examples["messages"]
        texts = [
            tokenizer.apply_chat_template(
                convo,
                tokenize=False,
                add_generation_prompt=False,
            )
            for convo in convos
        ]
        return {"text": texts}

    dataset = dataset.map(format_messages, batched=True)

    output_dir = "/tmp/retro-alpha-lora"
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=per_device_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_ratio=0.05,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="epoch",
        fp16=False,
        bf16=True,
        group_by_length=True,
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        tokenizer=tokenizer,
        args=training_args,
        max_seq_length=max_seq_length,
        dataset_text_field="text",
    )

    print("Starting training...")
    trainer.train()

    final_dir = f"{output_dir}/final"
    print(f"Saving LoRA adapter to {final_dir}")
    trainer.model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)

    if hf_token:
        print(f"Pushing LoRA adapter to {output_repo}")
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
        try:
            api.create_repo(repo_id=output_repo, exist_ok=True)
        except Exception as e:
            print(f"Could not create {output_repo}: {e}")
            # Fallback to user namespace
            me = api.whoami()["name"]
            output_repo = f"{me}/retro-alpha-nemotron-lora"
            api.create_repo(repo_id=output_repo, exist_ok=True)
        api.upload_folder(folder_path=final_dir, repo_id=output_repo)

    return f"Training complete. LoRA saved to {output_repo}"


@app.local_entrypoint()
def main():
    result = train.remote()
    print(result)
