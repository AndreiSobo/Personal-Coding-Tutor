import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json

MODEL_PATH = "../training/pact-qwen-merged"
TEST_DATA_PATH = "../data/test_cases.json"  # You'll create this
OUTPUT_PATH = "../data/test_responses.json"
# i'll have do download it from Hugging Face - its not saved locally.

def generate_responses():
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,  # consider implementing quant
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    
    # Load test cases (create from validation split or new problems)
    with open(TEST_DATA_PATH, 'r') as f:
        test_cases = json.load(f)
    
    responses = []
    
    for i, case in enumerate(test_cases):
        print(f"Generating response {i+1}/{len(test_cases)}...")
        
        messages = [
            {"role": "system", "content": "You are PACT, a Socratic Python coding tutor."},
            {"role": "user", "content": f"Problem: {case['problem_title']}\n\n{case['buggy_code']}\n\nI'm stuck, can you help?"}
        ]
        
        inputs = tokenizer.apply_chat_template(
            messages,
            return_tensors="pt",
            add_generation_prompt=True
        ).to(model.device)
        
        outputs = model.generate(
            inputs,
            max_new_tokens=200,
            temperature=0.7,
            do_sample=True,
        )
        
        response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        responses.append(response)
    
    # Save for evaluation
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(responses, f, indent=2)
    
    print(f"Saved {len(responses)} responses to {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_responses()