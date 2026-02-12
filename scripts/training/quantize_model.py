import os
import traceback
from huggingface_hub import HfApi, create_repo, upload_folder
from dotenv import load_dotenv
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

load_dotenv('../.env') 

HF_USERNAME = "AndreiSobo"
ORIGINAL_REPO_ID = "AndreiSobo/pact-qwen-tutor"
REPO_NAME = "pact-qwen-tutor-awq" 
NEW_REPO_ID = f"{HF_USERNAME}/{REPO_NAME}"
QUANT_MODEL_PATH = "./pact-qwen-awq-4bit"

# ========================================
# CUSTOM CALIBRATION DATA (Prevents Crashes)
# ========================================
def get_calib_dataset():
    """
    Returns a small list of Python code snippets and text to calibrate the model.
    This replaces the massive default download that was crashing the script.
    """
    print("Generating custom calibration data (Python-focused)...")
    return [
        "def hello_world():\n    print('Hello world')",
        "for i in range(10):\n    if i % 2 == 0:\n        print(i)",
        "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:",
        "import numpy as np\nx = np.array([1, 2, 3])",
        "def quicksort(arr):\n    if len(arr) <= 1: return arr",
        "Explain the difference between a list and a tuple in Python.",
        "To handle exceptions in Python, use the try-except block.",
        "def factorial(n):\n    return 1 if n == 0 else n * factorial(n-1)",
        "Reviewing code is an essential part of software engineering.",
        "The time complexity of binary search is O(log n).",
        "pandas is a powerful library for data manipulation and analysis.",
        "flask is a micro web framework written in Python.",
        "def merge_sort(arr):\n    if len(arr) > 1:\n        mid = len(arr)//2",
        # We repeat generic structures to ensure enough tokens for statistics
        "x = [i**2 for i in range(10)]",
        "with open('file.txt', 'r') as f:\n    content = f.read()",
    ] * 10  # Duplicate to create a sufficient batch size

# ========================================
# AUTHENTICATION
# ========================================
def get_hf_token():
    token = os.environ.get('HF_TOKEN')
    if token:
        print("✓ Using HF_TOKEN from environment")
        return token

# ========================================
# QUANTIZATION
# ========================================
def quantize_model(hf_token):
    print(f"\n--- Loading Model from {ORIGINAL_REPO_ID} ---")
    
    try:
        model = AutoAWQForCausalLM.from_pretrained(
            ORIGINAL_REPO_ID, 
            safetensors=True, 
            low_cpu_mem_usage=True,
            token=hf_token
        )
        tokenizer = AutoTokenizer.from_pretrained(
            ORIGINAL_REPO_ID, 
            trust_remote_code=True,
            token=hf_token
        )
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise e

    # AWQ Quantization Configuration
    quant_config = {
        "zero_point": True,
        "q_group_size": 128,
        "w_bit": 4,
        "version": "GEMM"
    }
    
    # Get the safe, custom calibration data
    calib_data = get_calib_dataset()

    print("\n--- Starting Quantization ---")
    print("(Calibrating on custom Python dataset to avoid OOM crashes)")
    
    # Pass the custom data here to override the default download
    model.quantize(tokenizer, quant_config=quant_config, calib_data=calib_data)
    
    print(f"\nSaving 4-bit model to: {QUANT_MODEL_PATH}...")
    model.save_quantized(QUANT_MODEL_PATH)
    tokenizer.save_pretrained(QUANT_MODEL_PATH)
    print("✓ Quantization complete!")

# ========================================
# MODEL CARD
# ========================================
def create_model_card():
    return f"""---
license: apache-2.0
base_model: {ORIGINAL_REPO_ID}
tags:
- education
- coding-tutor
- socratic
- python
- fine-tuned
- qwen2.5
- qlora
- awq
- 4-bit
quantized_by: autoawq
datasets:
- synthetic-socratic-coding
pipeline_tag: text-generation
---

# PACT - Personalised AI Coding Tutor (4-bit AWQ Quantized)

**This is the 4-bit AWQ quantized version of the original [PACT model](https://huggingface.co/{ORIGINAL_REPO_ID}).**

It is optimized for low-latency inference on GPUs with limited VRAM (e.g., NVIDIA T4, L4, or consumer RTX cards).

## Quantization Details
- **Method:** AWQ (Activation-aware Weight Quantization)
- **Precision:** 4-bit
- **Calibration Data:** Custom Python code snippets
"""

# ========================================
# MAIN
# ========================================
def main():
    hf_token = get_hf_token()
    if not hf_token: return 

    # Authenticate
    api = HfApi(token=hf_token)
    try:
        user_info = api.whoami()
        print(f"✓ Logged in as: {user_info['name']}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Quantize
    if not os.path.exists(QUANT_MODEL_PATH):
        os.makedirs(QUANT_MODEL_PATH, exist_ok=True)
        try:
            quantize_model(hf_token)
        except Exception as e:
            # FIX: Print the actual error trace
            print(f"\n❌ Quantization failed with error: {e}")
            traceback.print_exc()
            return
    else:
        print(f"\n! Found existing quantized model at {QUANT_MODEL_PATH}")
        print("! Skipping quantization step.")

    # Create Repo
    print(f"\n--- Preparing Upload to {NEW_REPO_ID} ---")
    try:
        create_repo(
            repo_id=NEW_REPO_ID,
            repo_type="model",
            exist_ok=True,
            private=False,
            token=hf_token
        )
    except Exception as e:
        print(f"❌ Repository creation failed: {e}")
        return

    # Save Card
    card = create_model_card()
    with open(os.path.join(QUANT_MODEL_PATH, "README.md"), "w", encoding='utf-8') as f:
        f.write(card)

    # Upload
    print("\nUploading Quantized model...")
    try:
        upload_folder(
            folder_path=QUANT_MODEL_PATH,
            repo_id=NEW_REPO_ID,
            repo_type="model",
            commit_message="upload of 4-bit AWQ quantized model",
            token=hf_token
        )
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        return

    print("\n✓ UPLOAD COMPLETE")

if __name__ == "__main__":
    main()