"""
Step 1: Prepare Source Problems from LeetCode Dataset
=====================================================
This script loads the newfacade/LeetCodeDataset from Hugging Face
and prepares a selection of problems for training data generation.

Output: data/source_problems.json
"""

from datasets import load_dataset
import json
import os

# Ensure data directory exists
os.makedirs('../data', exist_ok=True)

def main():
    print("Loading LeetCode dataset from Hugging Face...")
    print("(This may take a moment on first run as it downloads the dataset)")
    
    # Load the dataset
    ds = load_dataset("newfacade/LeetCodeDataset", split="train")
    
    print(f"Loaded {len(ds)} total problems")
    
    # Debug: Print first row to understand structure
    # for row in ds:
    #     print(f"type: {type(row)},")
    #     print("---")
    #     print(row)
    #     break
    
    # Filter for problems with necessary fields
    problems = []
    for row in ds:
        # Check if problem has necessary fields based on the actual dataset structure
        task_id = row.get('task_id')
        problem_description = row.get('problem_description')
        starter_code = row.get('starter_code')
        completion = row.get('completion')
        
        if task_id and problem_description and starter_code and completion:
            problems.append({
                'id': row.get('question_id'),
                'task_id': task_id,
                'title': task_id.replace('-', ' ').title(),  # Convert task_id to readable title
                'slug': task_id,
                'difficulty': row.get('difficulty', 'Medium'),
                'description': problem_description,
                'starter_code': starter_code,
                'solution': completion,
                'tags': row.get('tags', []),
                'entry_point': row.get('entry_point', ''),
                'test': row.get('test', ''),
                'prompt': row.get('prompt', ''),
                'query': row.get('query', ''),
                'response': row.get('response', ''),
                'input_output': row.get('input_output', []),
            })
    
    print(f"Found {len(problems)} problems with Python solutions")
    
    # Categorize by difficulty
    easy = [p for p in problems if p['difficulty'] == 'Easy']
    medium = [p for p in problems if p['difficulty'] == 'Medium']
    hard = [p for p in problems if p['difficulty'] == 'Hard']
    
    print(f"  Easy: {len(easy)}")
    print(f"  Medium: {len(medium)}")
    print(f"  Hard: {len(hard)}")
    
    # Select a balanced subset
    # Adjust these numbers based on how many training examples you want
    # 100 problems × 3 examples each = 300 training examples
    num_easy = min(50, len(easy))
    num_medium = min(30, len(medium))
    num_hard = min(20, len(hard))
    
    selected = easy[:num_easy] + medium[:num_medium] + hard[:num_hard]
    
    print(f"\nSelected {len(selected)} problems:")
    print(f"  Easy: {num_easy}")
    print(f"  Medium: {num_medium}")
    print(f"  Hard: {num_hard}")
    
    # Save to file
    output_path = '../data/source_problems.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(selected, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to {output_path}")
    
    # Print a sample
    print("\n--- Sample Problem ---")
    sample = selected[0]
    print(f"Task ID: {sample['task_id']}")
    print(f"Title: {sample['title']}")
    print(f"Difficulty: {sample['difficulty']}")
    print(f"Tags: {sample['tags']}")
    print(f"Description preview: {sample['description'][:200]}...")
    print(f"Entry point: {sample['entry_point']}")
    print(f"Has tests: {bool(sample['test'])}")
    print(f"Has input/output examples: {len(sample['input_output'])} examples")

if __name__ == "__main__":
    main()
