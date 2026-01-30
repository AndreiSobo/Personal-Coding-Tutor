"""
Upload Model to Hugging Face Hub
=================================
This script uploads the merged model to Hugging Face Hub
for use with the Inference API.

Input: ./pact-qwen-merged
Output: Uploaded to HuggingFace (your-username/pact-qwen-tutor)

Setup:
1. Create account at huggingface.co
2. Generate access token at huggingface.co/settings/tokens (with write access)
3. Add to .env: HF_TOKEN=your_token_here
   OR run: huggingface-cli login
"""

import os
from huggingface_hub import HfApi, create_repo, upload_folder
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')  # Load from scripts/.env

# ========================================
# CONFIGURATION
# ========================================

# Change this to your Hugging Face username
HF_USERNAME = "AndreiSobo"

# Repository name
REPO_NAME = "pact-qwen-tutor"

# Full repo ID
REPO_ID = f"{HF_USERNAME}/{REPO_NAME}"

# Local model path
MODEL_PATH = "./pact-qwen-merged"

# ========================================
# AUTHENTICATION
# ========================================

def get_hf_token():
    """
    Get HuggingFace token from environment or CLI login.
    Priority: HF_TOKEN env var > CLI stored token
    """
    # Try environment variable first (from .env file)
    token = os.environ.get('HF_TOKEN')
    
    if token:
        print("✓ Using HF_TOKEN from environment")
        return token
    
    # Fall back to CLI login (stored in ~/.huggingface/token)
    try:
        from huggingface_hub import HfFolder
        token = HfFolder.get_token()
        if token:
            print("✓ Using token from huggingface-cli login")
            return token
    except Exception:
        pass
    
    # No token found
    print("\n❌ No HuggingFace token found!")
    print("\nPlease authenticate using ONE of these methods:")
    print("\n1. Add to your .env file:")
    print("   HF_TOKEN=hf_your_token_here")
    print("\n2. Or run in terminal:")
    print("   huggingface-cli login")
    print("\nGet your token at: https://huggingface.co/settings/tokens")
    print("(Make sure to select 'Write' access when creating the token)")
    return None

# ========================================
# UPLOAD
# ========================================

def create_model_card():
    """Generate a README for the model."""
    
    card = f"""---
license: apache-2.0
base_model: Qwen/Qwen2.5-7B-Instruct
tags:
- education
- coding-tutor
- socratic
- python
- fine-tuned
- qwen2.5
- qlora
datasets:
- custom-synthetic-socratic-leetcode
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

## Training Details

- **Base model:** Qwen/Qwen2.5-7B-Instruct
- **Method:** QLoRA (4-bit quantization with LoRA rank-16 adapters)
- **Dataset:** 227 synthetic examples of coding errors with Socratic hints
- **Training:** 3 epochs, batch size 16, learning rate 2e-4
- **Hardware:** NVIDIA RTX 4090 (24GB VRAM)
- **Framework:** HuggingFace Transformers + PEFT + TRL

### Dataset Creation Process

The training dataset was generated through:
1. Sampling 100 LeetCode problems (Easy/Medium/Hard)
2. Using Claude Sonnet 4.5 to generate realistic student errors
3. Validating with GPT-4o to ensure quality (79.1% pass rate)
4. Formatting for Qwen 2.5 Instruct chat template

Error types include:
- Logic errors (48.5%)
- Edge case failures (19.4%)
- Off-by-one errors (18.5%)
- Missing base cases (7.5%)
- Wrong algorithms (3.5%)

## Evaluation Metrics

*Note: Metrics will be added after post-training evaluation*

The model will be evaluated on:
- **Code Leakage Rate (CLR):** Percentage of responses containing executable code (target: <5%)
- **Guiding Question Rate (GQR):** Percentage using Socratic questions (target: >70%)
- **Direct Answer Rate (DAR):** Percentage revealing solutions directly (target: <10%)
- **Error Identification Accuracy (EIA):** Correctly identifying the actual bug (target: >85%)
- **Factual Correctness Rate (FCR):** Technical accuracy of hints (target: >95%)

## Usage

### Basic Usage
````python
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load model and tokenizer
model = AutoModelForCausalLM.from_pretrained(
    "{HF_USERNAME}/{REPO_NAME}",
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("{HF_USERNAME}/{REPO_NAME}")

# Example conversation
messages = [
    {{
        "role": "system", 
        "content": "You are PACT, a Socratic Python coding tutor. Help students learn through guided questions and hints, not direct answers."
    }},
    {{
        "role": "user", 
        "content": \"\"\"Problem: Two Sum

Given an array of integers nums and an integer target, return indices of the two numbers that add up to target.

My code:
```python
def twoSum(nums, target):
    for i in range(len(nums)):
        for j in range(len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
```

I'm getting wrong answers for some test cases. Can you help me understand what's wrong?\"\"\"
    }}
]

# Generate response
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(model.device)

outputs = model.generate(
    **inputs,
    max_new_tokens=200,
    temperature=0.7,
    do_sample=True,
    top_p=0.9
)

response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
print(response)
````

### Expected Response Style

The model will provide Socratic guidance like:

> "Let's think about what happens when your loops run. When `i=0` and `j=0`, what values are you comparing? Is it valid for an element to be paired with itself in this problem? Consider what the problem statement says about using the same element twice."

Rather than directly stating:

> ❌ "Change `range(len(nums))` to `range(i+1, len(nums))` in the inner loop."

## Intended Use

This model is designed for **educational purposes**, specifically to:
- Help students learn Python programming through guided discovery
- Assist in debugging common coding errors
- Encourage critical thinking and problem-solving skills
- Provide formative feedback on coding assignments

**Not intended for:**
- Production code generation
- Automated grading systems
- Replacing human instruction entirely

## Limitations

- **Language:** Focused on Python; other languages not tested
- **Problem domains:** Optimized for algorithmic/LeetCode-style problems
- **Error types:** Trained on common student mistakes; may not handle edge cases well
- **Context length:** Limited to 2048 tokens per conversation
- **Socratic quality:** May occasionally be too direct or too vague

## Ethical Considerations

- Students should be encouraged to attempt problems independently before seeking hints
- Educators should review model responses for accuracy before sharing with students
- This tool supplements, not replaces, traditional learning resources
- Care taken to avoid revealing direct solutions that would enable plagiarism

## Citation

If you use this model in your research or educational materials, please cite:
````bibtex
@misc{{pact2026,
  author = {{Sobo, Andrei}},
  title = {{PACT: Personalised AI Coding Tutor - A Socratic Fine-Tuned Qwen 2.5 Model}},
  year = {{2026}},
  publisher = {{HuggingFace}},
  url = {{https://huggingface.co/{HF_USERNAME}/{REPO_NAME}}}
}}
````

## Acknowledgements

- **Base Model:** Qwen Team at Alibaba Cloud
- **Synthetic Data Generation:** Anthropic Claude Sonnet 4.5, OpenAI GPT-4o
- **Source Dataset:** LeetCode problems (newfacade/LeetCodeDataset)
- **Framework:** HuggingFace Transformers, PEFT, TRL, bitsandbytes

## License

This model inherits the Apache 2.0 license from Qwen 2.5 7B Instruct.

## Contact

For questions, issues, or feedback:
- **GitHub:** [Link to your repository]
- **Email:** [Your email if you want to share]
- **HuggingFace:** [@{HF_USERNAME}](https://huggingface.co/{HF_USERNAME})
"""
    return card


def main():
    print("=" * 60)
    print("Upload to Hugging Face Hub")
    print("=" * 60)
    
    # Get authentication token
    hf_token = get_hf_token()
    if not hf_token:
        return  # Error message already printed
    
    # Check model exists
    if not os.path.exists(MODEL_PATH):
        print(f"\n❌ Error: Model not found at {MODEL_PATH}")
        print("Run merge_weights.py first.")
        return
    
    print(f"\nRepository: {REPO_ID}")
    print(f"Model path: {MODEL_PATH}")
    
    # Initialize API with token
    api = HfApi(token=hf_token)
    
    # Verify authentication
    print("\nVerifying authentication...")
    try:
        user_info = api.whoami()
        print(f"✓ Logged in as: {user_info['name']}")
        
        # Verify username matches
        if user_info['name'] != HF_USERNAME:
            print(f"\n⚠️  Warning: Token belongs to '{user_info['name']}' but HF_USERNAME is set to '{HF_USERNAME}'")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Create repository
    print(f"\nCreating repository: {REPO_ID}")
    try:
        create_repo(
            repo_id=REPO_ID,
            repo_type="model",
            exist_ok=True,
            private=False,  # Set to True if you want it private initially
            token=hf_token
        )
        print("✓ Repository created/verified")
    except Exception as e:
        print(f"❌ Repository creation failed: {e}")
        return
    
    # Create and save model card
    print("\nGenerating model card...")
    card = create_model_card()
    readme_path = os.path.join(MODEL_PATH, "README.md")
    with open(readme_path, "w", encoding='utf-8') as f:
        f.write(card)
    print("✓ Model card generated")
    
    # Upload
    print("\n" + "=" * 60)
    print("UPLOADING MODEL")
    print("=" * 60)
    print("This may take 10-20 minutes depending on your connection...")
    print("(Uploading ~14GB of model files)")
    
    try:
        upload_folder(
            folder_path=MODEL_PATH,
            repo_id=REPO_ID,
            repo_type="model",
            commit_message="Upload PACT fine-tuned Qwen 2.5 7B model",
            token=hf_token
        )
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✓ UPLOAD COMPLETE")
    print("=" * 60)
    print(f"\nModel URL: https://huggingface.co/{REPO_ID}")
    print(f"Inference API: https://api-inference.huggingface.co/models/{REPO_ID}")
    print("\n🎉 Your model is now publicly available on HuggingFace!")
    print("\nNext steps:")
    print("1. Wait 5-10 minutes for model card to render")
    print("2. Test the Inference API endpoint")
    print("3. Update your web app to use this model")


if __name__ == "__main__":
    main()