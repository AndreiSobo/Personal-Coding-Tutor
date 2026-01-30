import os
import sys
import argparse
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    EarlyStoppingCallback
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
import wandb

# ========================================
# CONFIGURATION
# ========================================

# Model to fine-tune
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# Training data
DATA_PATH = "../data/qwen_training_data.jsonl"

# Output directory
OUTPUT_DIR = "./pact-qwen-tutor"

# Training hyperparameters (defaults)
DEFAULT_EPOCHS = 3
DEFAULT_BATCH_SIZE = 4
DEFAULT_GRADIENT_ACCUMULATION = 4  # Effective batch size = 4 * 4 = 16
DEFAULT_LEARNING_RATE = 2e-4
MAX_SEQ_LENGTH = 2048
WARMUP_STEPS = 100

# LoRA hyperparameters
LORA_R = 16              # Rank
LORA_ALPHA = 32          # Scaling factor
LORA_DROPOUT = 0.05

# WandB configuration
WANDB_ENTITY = "soboandrei-wandb"
WANDB_PROJECT = "PACT"

# ========================================
# ARGUMENT PARSING
# ========================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fine-tune Qwen 2.5 7B with QLoRA")
    
    # Testing arguments
    parser.add_argument("--max_steps", type=int, default=None,
                        help="Maximum training steps (for quick testing)")
    parser.add_argument("--max_examples", type=int, default=None,
                        help="Maximum examples to use (for quick testing)")
    
    # Training arguments
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                        help=f"Number of training epochs (default: {DEFAULT_EPOCHS})")
    parser.add_argument("--batch_size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Per-device batch size (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--learning_rate", type=float, default=DEFAULT_LEARNING_RATE,
                        help=f"Learning rate (default: {DEFAULT_LEARNING_RATE})")
    
    # WandB arguments
    parser.add_argument("--run_name", type=str, default=None,
                        help="WandB run name (default: auto-generated)")
    parser.add_argument("--no_wandb", action="store_true",
                        help="Disable WandB logging")
    
    return parser.parse_args()

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


def load_training_data(max_examples=None):
    """Load and prepare the training dataset."""
    
    print(f"Loading training data from {DATA_PATH}...")
    
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Training data not found: {DATA_PATH}")
    
    # Load full dataset
    dataset = load_dataset("json", data_files=DATA_PATH, split="train")
    
    # Limit examples if testing
    if max_examples is not None:
        print(f"Limiting to {max_examples} examples for testing")
        dataset = dataset.select(range(min(max_examples, len(dataset))))
    
    # Split into train/validation
    dataset_split = dataset.train_test_split(test_size=0.1, seed=42)
    
    print(f"Dataset split:")
    print(f"  Training: {len(dataset_split['train'])} examples")
    print(f"  Validation: {len(dataset_split['test'])} examples")
    
    return dataset_split


# ========================================
# TRAINING
# ========================================

def train():
    """Main training function."""
    
    # Parse arguments
    args = parse_args()
    
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
    dataset_split = load_training_data(max_examples=args.max_examples)
    
    # Generate run name
    if args.run_name is None:
        # Auto-generate based on parameters
        run_name = f"qwen-2.5-7b-qlora-e{args.epochs}-bs{args.batch_size}-lr{args.learning_rate}"
    else:
        run_name = args.run_name
    
    # Initialize WandB
    wandb_run = None
    if not args.no_wandb:
        print("\nInitializing Weights & Biases...")
        wandb_run = wandb.init(
            entity=WANDB_ENTITY,
            project=WANDB_PROJECT,
            name=run_name,
            config={
                "model_id": MODEL_ID,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "gradient_accumulation": DEFAULT_GRADIENT_ACCUMULATION,
                "learning_rate": args.learning_rate,
                "lora_r": LORA_R,
                "lora_alpha": LORA_ALPHA,
                "lora_dropout": LORA_DROPOUT,
                "max_seq_length": MAX_SEQ_LENGTH,
                "warmup_steps": WARMUP_STEPS,
                "dataset_size_train": len(dataset_split['train']),
                "dataset_size_val": len(dataset_split['test']),
                "optimizer": "paged_adamw_8bit",
            }
        )
        print(f"WandB run: {wandb_run.name}")
        print(f"Dashboard: {wandb_run.url}")
    
    # Training configuration
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps if args.max_steps is not None else -1,  # -1 means use epochs
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=DEFAULT_GRADIENT_ACCUMULATION,
        learning_rate=args.learning_rate,
        warmup_steps=WARMUP_STEPS,
        
        # Logging
        logging_steps=10,
        logging_first_step=True,
        
        # Evaluation
        eval_strategy="steps",
        eval_steps=50,
        
        # Checkpointing
        save_steps=100,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        
        # Optimization
        fp16=True,
        optim="paged_adamw_8bit",
        
        # Model settings
        max_seq_length=MAX_SEQ_LENGTH,
        packing=False,  # Don't pack sequences for chat format
        
        # Gradient checkpointing for memory efficiency
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        
        # WandB
        report_to="wandb" if not args.no_wandb else "none",
        run_name=run_name,
    )
    
    # Initialize trainer
    print("\nInitializing trainer...")
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset_split["train"],
        eval_dataset=dataset_split["test"],  # FIXED: was test_dataset
        tokenizer=tokenizer,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)] if args.max_steps is None else [],
    )
    
    # Train
    print("\n" + "=" * 60)
    print("STARTING TRAINING")
    print("=" * 60)
    print(f"Configuration:")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size} x {DEFAULT_GRADIENT_ACCUMULATION} = {args.batch_size * DEFAULT_GRADIENT_ACCUMULATION}")
    print(f"  Learning rate: {args.learning_rate}")
    print(f"  Max sequence length: {MAX_SEQ_LENGTH}")
    if args.max_steps:
        print(f"  Max steps: {args.max_steps} (TESTING MODE)")
    print("-" * 60)
    
    try:
        # Run training
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
        
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("TRAINING INTERRUPTED")
        print("=" * 60)
        print("Saving checkpoint...")
        trainer.save_model(OUTPUT_DIR + "_interrupted")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("TRAINING FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        raise
        
    finally:
        # Always finish WandB run
        if wandb_run is not None:
            print("\nFinalizing WandB...")
            wandb.finish()


if __name__ == "__main__":
    train()