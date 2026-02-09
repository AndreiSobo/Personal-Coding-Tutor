"""
Extract Test Cases from Training Data
======================================
Recreates the exact validation split used during training
"""

import json
from datasets import load_dataset

# Load your training data 
def main():
    dataset = load_dataset("json", data_files="../data/qwen_training_data.jsonl", split="train")

    # Recreate the same split from training
    dataset_split = dataset.train_test_split(test_size=0.1, seed=42)
    validation_data = dataset_split['test']
    # Extract test cases (without hints)
    test_cases = []
    for example in validation_data:
        messages = example['messages']
        
        # Extract user message (contains problem + buggy code)
        user_message = next(m['content'] for m in messages if m['role'] == 'user')
        
        # Extract the hint (for evaluation comparison, but won't be shown to model)
        
        # Parse user message to extract components
        # Format: "Problem: [title]\n\n[description]\n\nMy code:\n```python\n[code]\n```\n\n[issue]\n\nCan you give me a hint?"
        
        test_cases.append({
            "full_user_message": user_message,
            "messages": [
                {"role": "system", "content": messages[0]['content']},
                {"role": "user", "content": user_message}
            ]
        })

    # Save test cases
    with open("../data/test_cases.json", 'w') as f:
        json.dump(test_cases, f, indent=2)

    print(f"✅ Saved {len(test_cases)} test cases")

if __name__ == "__main__":
    main()
