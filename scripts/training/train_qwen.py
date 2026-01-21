"""
Qwen 2.5 7B Fine-Tuning Script using QLoRA
==========================================
This script fine-tunes Qwen 2.5 7B Instruct on the Socratic hint dataset
using QLoRA (Quantized Low-Rank Adaptation) for memory efficiency.

Requirements:
- GPU with at least 12GB VRAM (RTX 4070 or better)
- Or run on RunPod/Colab with better GPU

Input: ../data/training_data.jsonl
Output: ./pact-qwen-tutor (adapter weights)
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# ========================================
# CONFIGURATION
# ========================================

# Model to fine-tune
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# Training data
DATA_PATH = "../data/training_data.jsonl"

# Output directory
OUTPUT_DIR = "./pact-qwen-tutor"

# Training hyperparameters
EPOCHS = 3
BATCH_SIZE = 4
GRADIENT_ACCUMULATION = 4  # Effective batch size = 4 * 4 = 16
LEARNING_RATE = 2e-4
MAX_SEQ_LENGTH = 2048
WARMUP_STEPS = 100

# LoRA hyperparameters
LORA_R = 16              # Rank
LORA_ALPHA = 32          # Scaling factor
LORA_DROPOUT = 0.05

# ========================================
# SETUP
# ========================================

def setup_model_and_tokenizer():
    """Load and configure the model with 4-bit quantization."""
    
    print(f"Loading {MODEL_ID} with 4-bit quantization...")
    
    # 4-bit quantization config (QLoRA)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True
    )
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        trust_remote_code=True
    )
    
    # Set padding token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)
    
    print(f"Model loaded. Parameters: {model.num_parameters():,}")
    
    return model, tokenizer


def setup_lora(model):
    """Configure LoRA adapters."""
    
    print("Configuring LoRA adapters...")
    
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
            "gate_proj", "up_proj", "down_proj"       # MLP
        ],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, lora_config)
    
    # Print trainable parameters
    trainable, total = model.get_nb_trainable_parameters()
    print(f"Trainable parameters: {trainable:,} / {total:,} ({100 * trainable / total:.2f}%)")
    
    return model


def load_training_data():
    """Load and prepare the training dataset."""
    
    print(f"Loading training data from {DATA_PATH}...")
    
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Training data not found: {DATA_PATH}")
    
    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    
    print(f"Loaded {len(dataset)} training examples")
    
    return dataset


def formatting_func(example):
    """Format examples for the trainer."""
    # The SFTTrainer will handle chat template formatting
    return example


# ========================================
# TRAINING
# ========================================

def train():
    """Main training function."""
    
    print("=" * 60)
    print("PACT - Qwen 2.5 7B Fine-Tuning")
    print("=" * 60)
    
    # Check GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
    else:
        print("WARNING: No GPU detected. Training will be very slow!")
    
    # Load components
    model, tokenizer = setup_model_and_tokenizer()
    model = setup_lora(model)
    dataset = load_training_data()
    
    # Training configuration
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE,
        warmup_steps=WARMUP_STEPS,
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        fp16=True,
        optim="paged_adamw_8bit",
        max_seq_length=MAX_SEQ_LENGTH,
        packing=False,  # Don't pack sequences for chat format
        report_to="none",  # Disable wandb
        
        # Gradient checkpointing for memory efficiency
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    
    # Initialize trainer
    print("\nInitializing trainer...")
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )
    
    # Train
    print("\n" + "=" * 60)
    print("STARTING TRAINING")
    print("=" * 60)
    print(f"Epochs: {EPOCHS}")
    print(f"Batch size: {BATCH_SIZE} x {GRADIENT_ACCUMULATION} = {BATCH_SIZE * GRADIENT_ACCUMULATION}")
    print(f"Learning rate: {LEARNING_RATE}")
    print(f"Max sequence length: {MAX_SEQ_LENGTH}")
    print("-" * 60)
    
    trainer.train()
    
    # Save the final model
    print("\nSaving model...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Model saved to: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("1. Run merge_weights.py to merge LoRA adapters")
    print("2. Run upload_to_hf.py to upload to Hugging Face Hub")


if __name__ == "__main__":
    train()
