"""
Step 4: Revise Problematic Examples
====================================
This script takes examples marked as "needs_revision" and uses Claude
to fix the Socratic hints based on the validation feedback.

Input: data/examples_needs_revision.json
Output: data/training_dataset_final.json (combined with passed examples)
"""

import anthropic
import json
import time
import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

# Initialize Anthropic client
client = anthropic.Anthropic()

REVISION_PROMPT = """
You are fixing a Socratic hint for a coding tutor training dataset.

## Original Example

**Problem:** {problem_title}

**Student's Buggy Code:**
```python
{buggy_code}
```

**What's Actually Wrong:** {bug_explanation}

**Original Hint (NEEDS FIXING):** 
"{original_hint}"

## Issues Identified
{issues}

## Suggested Improvement
{suggestion}

## Your Task
Write a NEW Socratic hint that fixes all the issues above.

The hint MUST:
✅ Guide through questions or gentle suggestions
✅ Help the student discover the issue themselves
✅ Be encouraging and supportive
✅ Be 2-4 sentences long

The hint must NEVER:
❌ Contain any code
❌ Directly name the fix ("change X to Y")
❌ Use directive language ("you should", "you need to")
❌ Directly state what's wrong ("your loop is wrong")

## Response
Respond with ONLY the new hint text. No explanations, no quotes, just the hint itself.
"""


def revise_hint(example: Dict, max_retries: int = 3) -> str:
    """Revise a problematic hint using Claude."""
    
    validation = example.get('validation', {})
    issues = validation.get('issues', ['Hint needs to be more Socratic'])
    suggestion = validation.get('suggested_improvement', 'Make the hint more Socratic - guide without revealing')
    
    prompt = REVISION_PROMPT.format(
        problem_title=example['problem_title'],
        buggy_code=example['buggy_code'],
        bug_explanation=example['bug_explanation'],
        original_hint=example['socratic_hint'],
        issues='\n'.join(f"- {issue}" for issue in issues),
        suggestion=suggestion
    )
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            new_hint = response.content[0].text.strip()
            
            # Basic validation - hint shouldn't be too short or contain code
            if len(new_hint) < 30:
                print(f"      Attempt {attempt + 1}: Hint too short, retrying...")
                continue
            
            if '```' in new_hint or 'def ' in new_hint:
                print(f"      Attempt {attempt + 1}: Hint contains code, retrying...")
                continue
            
            # Remove quotes if the model wrapped the hint in them
            if new_hint.startswith('"') and new_hint.endswith('"'):
                new_hint = new_hint[1:-1]
            if new_hint.startswith("'") and new_hint.endswith("'"):
                new_hint = new_hint[1:-1]
            
            return new_hint
            
        except Exception as e:
            print(f"      Attempt {attempt + 1}: Error: {e}")
        
        time.sleep(1)
    
    # Return original if all retries failed
    return example['socratic_hint']


def main():
    # Check for API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY not found in environment")
        return
    
    # Load examples needing revision
    revision_path = '../data/examples_needs_revision.json'
    passed_path = '../data/examples_passed.json'
    
    if not os.path.exists(revision_path):
        print(f"Error: {revision_path} not found. Run step3_validate_examples.py first.")
        return
    
    if not os.path.exists(passed_path):
        print(f"Error: {passed_path} not found. Run step3_validate_examples.py first.")
        return
    
    with open(revision_path, 'r', encoding='utf-8') as f:
        needs_revision = json.load(f)
    
    with open(passed_path, 'r', encoding='utf-8') as f:
        passed = json.load(f)
    
    print(f"Loaded {len(passed)} passed examples")
    print(f"Loaded {len(needs_revision)} examples needing revision")
    print("-" * 50)
    
    if not needs_revision:
        print("No examples need revision. Combining passed examples only.")
        final_dataset = passed
    else:
        print("Revising hints using Claude...")
        
        revised = []
        for i, example in enumerate(needs_revision):
            print(f"[{i+1}/{len(needs_revision)}] {example['problem_title']} - {example['error_type']}")
            
            original_hint = example['socratic_hint']
            new_hint = revise_hint(example)
            
            if new_hint != original_hint:
                example['socratic_hint'] = new_hint
                example['original_hint'] = original_hint
                example['was_revised'] = True
                print(f"    ✓ Revised")
            else:
                example['was_revised'] = False
                print(f"    ⚠ Kept original (revision failed)")
            
            revised.append(example)
            
            # Rate limiting
            time.sleep(0.5)
        
        # Combine passed and revised
        final_dataset = passed + revised
    
    # Remove validation metadata (not needed for training)
    for example in final_dataset:
        example.pop('validation', None)
    
    # Save final dataset
    output_path = '../data/training_dataset_final.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_dataset, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "=" * 50)
    print("REVISION COMPLETE")
    print("=" * 50)
    print(f"Total examples in final dataset: {len(final_dataset)}")
    print(f"  - Originally passed: {len(passed)}")
    print(f"  - Revised: {len([e for e in final_dataset if e.get('was_revised')])}")
    print(f"\nOutput saved to: {output_path}")
    
    # Show sample revised hint
    revised_examples = [e for e in final_dataset if e.get('was_revised')]
    if revised_examples:
        sample = revised_examples[0]
        print("\n--- Sample Revision ---")
        print(f"Problem: {sample['problem_title']}")
        print(f"Original: {sample.get('original_hint', 'N/A')[:100]}...")
        print(f"Revised:  {sample['socratic_hint'][:100]}...")


if __name__ == "__main__":
    main()
