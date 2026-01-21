"""
Upload Model to Hugging Face Hub
=================================
This script uploads the merged model to Hugging Face Hub
for use with the Inference API.

Input: ./pact-qwen-merged
Output: Uploaded to HuggingFace (your-username/pact-qwen-tutor)

Setup:
1. Create account at huggingface.co
2. Generate access token at huggingface.co/settings/tokens
3. Run: huggingface-cli login
"""

import os
from huggingface_hub import HfApi, create_repo, upload_folder

# ========================================
# CONFIGURATION
# ========================================

# Change this to your Hugging Face username
HF_USERNAME = "your-username"

# Repository name
REPO_NAME = "pact-qwen-tutor"

# Full repo ID
REPO_ID = f"{HF_USERNAME}/{REPO_NAME}"

# Local model path
MODEL_PATH = "./pact-qwen-merged"

# ========================================
# UPLOAD
# ========================================

def create_model_card():
    """Generate a README for the model."""
    
    card = """---
license: apache-2.0
base_model: Qwen/Qwen2.5-7B-Instruct
tags:
- education
- coding-tutor
- socratic
- python
- fine-tuned
language:
- en
pipeline_tag: text-generation
---

# PACT - Personalised AI Coding Tutor

This model is a fine-tuned version of Qwen 2.5 7B Instruct, designed to act as a **Socratic coding tutor** for Python programming.

## Model Description

PACT (Personalised AI Coding Tutor) is trained to:
- Provide **guiding hints** rather than direct solutions
- Ask **Socratic questions** to help students discover answers themselves
- Identify errors without revealing the fix
- Be encouraging and supportive in tone

## Training

- **Base model:** Qwen/Qwen2.5-7B-Instruct
- **Method:** QLoRA (4-bit quantization with LoRA adapters)
- **Dataset:** Synthetic Socratic dialogue pairs generated for coding errors

## Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("YOUR_USERNAME/pact-qwen-tutor")
tokenizer = AutoTokenizer.from_pretrained("YOUR_USERNAME/pact-qwen-tutor")

messages = [
    {"role": "system", "content": "You are PACT, a Socratic Python coding tutor."},
    {"role": "user", "content": "Problem: Two Sum\\n\\nMy code:\\n```python\\ndef twoSum(nums, target):\\n    for i in range(len(nums)):\\n        for j in range(len(nums)):\\n            if nums[i] + nums[j] == target:\\n                return [i, j]\\n```\\n\\nI'm getting wrong answers. Can you help?"}
]

text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=200)
print(tokenizer.decode(outputs[0]))
```

## Intended Use

This model is designed for educational purposes, specifically to help students learn Python programming through guided discovery rather than direct answers.

## Limitations

- Focused on Python; may not perform well on other languages
- Designed for common programming errors; may struggle with advanced concepts
- Should be used as a learning aid, not a replacement for human instruction

## Citation

If you use this model, please cite:

```
@misc{pact-tutor,
  author = {Your Name},
  title = {PACT: Personalised AI Coding Tutor},
  year = {2026},
  publisher = {Hugging Face},
  howpublished = {\\url{https://huggingface.co/YOUR_USERNAME/pact-qwen-tutor}}
}
```
"""
    return card


def main():
    print("=" * 60)
    print("Upload to Hugging Face Hub")
    print("=" * 60)
    
    # Check model exists
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model not found at {MODEL_PATH}")
        print("Run merge_weights.py first.")
        return
    
    # Check username is set
    if HF_USERNAME == "your-username":
        print("Error: Please edit this script and set HF_USERNAME to your Hugging Face username")
        return
    
    print(f"Repository: {REPO_ID}")
    print(f"Model path: {MODEL_PATH}")
    
    # Initialize API
    api = HfApi()
    
    # Check if logged in
    try:
        user_info = api.whoami()
        print(f"Logged in as: {user_info['name']}")
    except Exception:
        print("\nError: Not logged in to Hugging Face")
        print("Run: huggingface-cli login")
        return
    
    # Create repository
    print(f"\nCreating repository: {REPO_ID}")
    try:
        create_repo(
            repo_id=REPO_ID,
            repo_type="model",
            exist_ok=True,
            private=False  # Set to True if you want it private initially
        )
        print("Repository created/verified")
    except Exception as e:
        print(f"Repository creation: {e}")
    
    # Create and save model card
    print("\nGenerating model card...")
    card = create_model_card()
    readme_path = os.path.join(MODEL_PATH, "README.md")
    with open(readme_path, "w") as f:
        f.write(card.replace("YOUR_USERNAME", HF_USERNAME))
    
    # Upload
    print("\nUploading model (this may take a while)...")
    
    upload_folder(
        folder_path=MODEL_PATH,
        repo_id=REPO_ID,
        repo_type="model",
        commit_message="Upload PACT fine-tuned model"
    )
    
    print("\n" + "=" * 60)
    print("UPLOAD COMPLETE")
    print("=" * 60)
    print(f"Model URL: https://huggingface.co/{REPO_ID}")
    print(f"\nInference API: https://api-inference.huggingface.co/models/{REPO_ID}")
    print("\nYou can now use this model in your PACT application!")


if __name__ == "__main__":
    main()
