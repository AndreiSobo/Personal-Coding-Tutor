"""
Merge LoRA Weights into Base Model
===================================
After fine-tuning with QLoRA, this script merges the adapter weights
into the base model for easier deployment.

Input: ./pact-qwen-tutor (adapter weights)
Output: ./pact-qwen-merged (full merged model)
"""

import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ========================================
# CONFIGURATION
# ========================================

BASE_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
ADAPTER_PATH = "./pact-qwen-tutor"
OUTPUT_PATH = "./pact-qwen-merged"

# ========================================
# MERGE
# ========================================

def main():
    print("=" * 60)
    print("Merging LoRA Weights into Base Model")
    print("=" * 60)
    
    # Check adapter exists
    if not os.path.exists(ADAPTER_PATH):
        print(f"Error: Adapter not found at {ADAPTER_PATH}")
        print("Run train_qwen.py first.")
        return
    
    # Load base model (full precision for merging)
    print(f"\nLoading base model: {BASE_MODEL_ID}")
    print("(This may take a few minutes...)")
    
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_ID,
        trust_remote_code=True
    )
    
    # Load LoRA adapter
    print(f"\nLoading LoRA adapter from: {ADAPTER_PATH}")
    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    
    # Merge weights
    print("\nMerging weights...")
    merged_model = model.merge_and_unload()
    
    # Save merged model
    print(f"\nSaving merged model to: {OUTPUT_PATH}")
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    merged_model.save_pretrained(
        OUTPUT_PATH,
        safe_serialization=True,  # Save as .safetensors
        max_shard_size="5GB"
    )
    tokenizer.save_pretrained(OUTPUT_PATH)
    
    # Calculate size
    total_size = 0
    for f in os.listdir(OUTPUT_PATH):
        total_size += os.path.getsize(os.path.join(OUTPUT_PATH, f))
    
    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"Output: {OUTPUT_PATH}")
    print(f"Size: {total_size / 1e9:.2f} GB")
    print("\nNext step: Run upload_to_hf.py to upload to Hugging Face Hub")


if __name__ == "__main__":
    main()
