"""
Modal fine-tuning script for Retro Alpha.
Fine-tunes nvidia/Nemotron-3-Nano-4B-Chat with LoRA on the Retro Alpha dataset.

Usage:
    modal run training.modal_train
"""

import os

import modal

# Modal configuration
app = modal.App("retro-alpha-finetune")

# Image with training dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch==2.3.0",
        "transformers==4.41.0",
        "datasets==2.19.0",
        "peft==0.11.0",
        "trl==0.8.6",
        "accelerate==0.30.0",
        "bitsandbytes==0.43.0",
        "huggingface_hub==0.23.0",
        "wandb",
    )
)

# Secrets for HF and W&B
secrets = [
    modal.Secret.from_name("hf-token", required=False),
    modal.Secret.from_name("wandb-token", required=False),
]

# A100 40GB GPU
GPU_CONFIG = modal.gpu.A100(size="40GB")


@app.function(
    image=image,
    gpu=GPU_CONFIG,
    timeout=60 * 60 * 4,  # 4 hours
    secrets=secrets,
)
def train(
    base_model: str = "nvidia/Nemotron-3-Nano-4B-Chat",
    dataset_repo: str = "build-small-hackathon/retro-alpha-dataset",
    output_repo: str = "build-small-hackathon/retro-alpha-nemotron-lora",
    num_epochs: int = 3,
    batch_size: int = 4,
    gradient_accumulation_steps: int = 2,
    learning_rate: float = 2e-4,
    lora_r: int = 64,
    lora_alpha: int = 128,
    max_seq_length: int = 1024,
):
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from trl import SFTTrainer

    # Login to HF if token available
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        from huggingface_hub import login
        login(token=hf_token)

    print(f"Loading base model: {base_model}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print(f"Loading dataset: {dataset_repo}")
    dataset = load_dataset(dataset_repo, split="train")

    def format_messages(example):
        messages = example["messages"]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    dataset = dataset.map(format_messages, remove_columns=dataset.column_names)

    output_dir = "/tmp/retro-alpha-lora"
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        optim="paged_adamw_8bit",
        learning_rate=learning_rate,
        warmup_ratio=0.05,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy="epoch",
        fp16=False,
        bf16=True,
        group_by_length=True,
        report_to="none",
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

    print(f"Saving LoRA adapter to {output_dir}/final")
    trainer.model.save_pretrained(f"{output_dir}/final")
    tokenizer.save_pretrained(f"{output_dir}/final")

    # Push to HF
    if hf_token:
        print(f"Pushing LoRA adapter to {output_repo}")
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
        api.create_repo(repo_id=output_repo, exist_ok=True)
        api.upload_folder(folder_path=f"{output_dir}/final", repo_id=output_repo)

    return f"Training complete. LoRA saved to {output_repo}"


@app.local_entrypoint()
def main():
    result = train.remote()
    print(result)
