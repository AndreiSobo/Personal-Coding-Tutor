"""
Step 5: Format Dataset for Qwen Training
==========================================
This script converts the validated examples into the chat format
required for fine-tuning Qwen 2.5 Instruct.

Input: data/training_dataset_final.json
Output: data/qwen_training_data.jsonl (JSONL format for training), qwen_training_samples.json
"""

import json
import os
from typing import Dict
from collections import Counter

# Minimal system prompt - fine-tuning handles the behaviour
SYSTEM_PROMPT = "You are PACT, a Socratic Python coding tutor. Help students learn through guided questions and hints, not direct answers."


def convert_to_qwen_chat_format(example: Dict) -> Dict:
    """Convert a training example to Qwen 2.5 Instruct chat template format."""
    
    # Truncate description if too long to fit in context
    description = example['problem_description']
    if len(description) > 1500:
        description = description[:1500] + "\n[...]"
    
    # User message simulates a student asking for help
    user_content = f"""Problem: {example['problem_title']}

{description}

My code:
```python
{example['buggy_code']}
```

I'm stuck and not sure what's wrong. Can you help me understand the issue?"""

    # Assistant response is the Socratic hint
    assistant_content = example['socratic_hint']
    
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
    }


def convert_with_error_message(example: Dict) -> Dict:
    """Alternative format: include an error message if applicable."""
    
    description = example['problem_description']
    if len(description) > 1500:
        description = description[:1500] + "\n[...]"
    
    # Simulate having an error message for runtime/syntax errors
    error_type = example.get('error_type', '')
    error_hint = ""
    if error_type in ['syntax_error', 'type_error']:
        error_hint = "\n\nWhen I run it, I get an error."
    elif error_type in ['off_by_one', 'edge_case', 'infinite_loop']:
        error_hint = "\n\nIt runs but gives wrong output for some test cases."
    elif error_type == 'wrong_algorithm':
        error_hint = "\n\nIt's too slow and times out on large inputs."
    
    user_content = f"""Problem: {example['problem_title']}

{description}

My code:
```python
{example['buggy_code']}
```{error_hint}

Can you give me a hint?"""

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": example['socratic_hint']}
        ]
    }


def main():
    # Load final dataset
    input_path = '../data/training_dataset_final.json'
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        examples = json.load(f)
    
    print(f"Loaded {len(examples)} examples")

    # error type distribution
    error_types = Counter(ex['error_type'] for ex in examples)
    print("\nError type distribution:")
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count}")

    # Remove validation metadata
    for example in examples:
        example.pop('validation', None)

    print("Converting to Qwen chat format...")
    
    # Convert all examples
    formatted = []
    for example in examples:
        # Use the version with error messages for variety
        formatted_example = convert_with_error_message(example)
        formatted.append(formatted_example)
    
    # Save as JSONL (one JSON object per line - required format for training)
    output_path = '../data/qwen_training_data.jsonl'
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in formatted:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"Saved {len(formatted)} examples to {output_path}")
    
    # Also save a few samples for manual inspection
    samples_path = '../data/qwen_training_samples.json'
    with open(samples_path, 'w', encoding='utf-8') as f:
        json.dump(formatted[:5], f, indent=2, ensure_ascii=False)
    
    print(f"Saved 5 samples to {samples_path} for inspection")
    
    # Calculate statistics
    total_tokens_estimate = 0
    for item in formatted:
        # Rough estimate: 1 token ≈ 4 characters
        for msg in item['messages']:
            total_tokens_estimate += len(msg['content']) // 4
    
    print("\n" + "=" * 50)
    print("FORMAT COMPLETE")
    print("=" * 50)
    print(f"Total examples: {len(formatted)}")
    print(f"Estimated total tokens: ~{total_tokens_estimate:,}")
    print(f"Average tokens per example: ~{total_tokens_estimate // len(formatted):,}")
    
    # Show a sample
    print("\n--- Sample Formatted Example ---")
    sample = formatted[0]
    print(f"System: {sample['messages'][0]['content'][:80]}...")
    print(f"User: {sample['messages'][1]['content'][:150]}...")
    print(f"Assistant: {sample['messages'][2]['content'][:150]}...")


if __name__ == "__main__":
    main()
