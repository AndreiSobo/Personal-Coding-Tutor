import torch
import gc
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import os

# Define the models to evaluate
MODELS = {
    "Original (FP16)": "AndreiSobo/pact-qwen-tutor",
    "Quantized (AWQ)": "AndreiSobo/pact-qwen-tutor-awq"
}

TEST_DATA_PATH = "../data/test_cases.json"
OUTPUT_PATH = "../data/test_responses_comparison.json"

def cleanup_vram():
    """Force garbage collection to free VRAM between models."""
    gc.collect()
    torch.cuda.empty_cache()
    print("   (VRAM cleared)")

def generate_responses():
    # 1. Load Test Cases
    if not os.path.exists(TEST_DATA_PATH):
        print(f"❌ Error: {TEST_DATA_PATH} not found. Run generate_test_cases.py first.")
        return

    with open(TEST_DATA_PATH, 'r') as f:
        test_cases = json.load(f)
    
    # Dictionary to store responses from ALL models
    all_responses = {}

    # 2. Iterate through each model
    for model_name, repo_id in MODELS.items():
        print(f"\n{'='*60}")
        print(f"GENERATING RESPONSES FOR: {model_name}")
        print(f"Repo: {repo_id}")
        print(f"{'='*60}")

        try:
            # Load Tokenizer
            tokenizer = AutoTokenizer.from_pretrained(repo_id, trust_remote_code=True)
            
            # Load Model
            print("Loading model...")
            model = AutoModelForCausalLM.from_pretrained(
                repo_id,
                torch_dtype="auto", 
                device_map="auto",
                trust_remote_code=True
            )
            
            model_responses = []

            for i, case in enumerate(test_cases):
                print(f"\rProcessing {i+1}/{len(test_cases)}...", end="", flush=True)

                # Format input using the model's chat template
                # We assume the test case has "full_user_message" or we reconstruct it
                user_content = case.get("full_user_message", "")
                if not user_content:
                     # Fallback reconstruction
                     user_content = f"Problem: {case.get('problem_title', 'Unknown')}\n\n{case.get('buggy_code', '')}\n\nI'm stuck, can you help?"

                messages = [
                    {"role": "system", "content": "You are PACT, a Socratic Python coding tutor."},
                    {"role": "user", "content": user_content}
                ]

                inputs = tokenizer.apply_chat_template(
                    messages,
                    return_tensors="pt",
                    add_generation_prompt=True
                ).to(model.device)

                # Generate
                with torch.no_grad():
                    outputs = model.generate(
                        inputs,
                        max_new_tokens=256, # Increased slightly for Socratic explanations
                        temperature=0.6,    # Slightly lower for more stable comparison
                        do_sample=True,
                        top_p=0.9
                    )

                response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
                model_responses.append(response)

            # Store results
            all_responses[model_name] = model_responses
            print(f"\n✅ Completed {len(model_responses)} responses for {model_name}")

            # CRITICAL: Delete model and clear VRAM before loading the next one
            del model
            del tokenizer
            cleanup_vram()

        except Exception as e:
            print(f"\n❌ Error evaluating {model_name}: {e}")
            continue

    # 3. Save Combined Results
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(all_responses, f, indent=2)

    print(f"\n💾 Saved comparative responses to {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_responses()