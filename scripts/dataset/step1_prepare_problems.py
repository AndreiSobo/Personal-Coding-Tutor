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
    
    # Filter for problems with Python solutions
    problems = []
    for row in ds:
        # Check if problem has necessary fields
        python_solution = row.get('python') or row.get('python_solution') or row.get('code_python')
        content = row.get('content') or row.get('description') or row.get('question')
        
        if python_solution and content:
            problems.append({
                'id': row.get('id') or row.get('question_id') or row.get('frontend_question_id'),
                'title': row.get('title', 'Unknown'),
                'slug': row.get('slug') or row.get('title_slug', ''),
                'difficulty': row.get('difficulty', 'Medium'),
                'description': content,
                'solution': python_solution,
                'tags': row.get('tags') or row.get('topicTags') or [],
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
    print(f"Title: {sample['title']}")
    print(f"Difficulty: {sample['difficulty']}")
    print(f"Tags: {sample['tags']}")
    print(f"Description preview: {sample['description'][:200]}...")

if __name__ == "__main__":
    main()
