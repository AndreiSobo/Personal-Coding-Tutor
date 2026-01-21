"""
Step 2: Generate Training Examples using Claude
================================================
This script uses Claude to generate realistic student errors
and Socratic hints for each problem.

Input: data/source_problems.json
Output: data/generated_examples_raw.json
"""

import anthropic
import json
import time
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

# Initialize Anthropic client
client = anthropic.Anthropic()

GENERATION_PROMPT = """
You are generating training data for a Socratic coding tutor called PACT. Your task is to create realistic student errors and appropriate pedagogical hints.

## Problem Information
Title: {title}
Difficulty: {difficulty}
Description: 
{description}

## Correct Solution
```python
{solution}
```

## Your Task
Generate 3 different examples of common student mistakes for this problem. Each example should represent a REALISTIC error that a student learning Python might make.

For each example, provide:
1. `error_type`: One of ["off_by_one", "logic_error", "syntax_error", "type_error", "edge_case", "wrong_algorithm", "missing_base_case", "infinite_loop", "wrong_data_structure"]
2. `buggy_code`: A complete, runnable (but incorrect) solution that a real student might write. Include the full function definition.
3. `bug_explanation`: What's actually wrong (this is for our records, NOT shown to student)
4. `socratic_hint`: A guiding hint that helps WITHOUT revealing the answer

## CRITICAL RULES FOR SOCRATIC HINTS
The hint MUST:
✅ Ask a guiding question OR point toward the problem area
✅ Be encouraging and supportive in tone
✅ Help the student discover the issue themselves

The hint must NEVER:
❌ Contain any code snippets
❌ Name the specific fix (e.g., never say "change X to Y")
❌ Use directive phrases like "you should", "you need to", "the solution is"
❌ Directly state what's wrong (e.g., "your loop condition is wrong")

## Examples of GOOD vs BAD hints

For an off-by-one error in a loop:
- ❌ BAD: "Change `i <= len(arr)` to `i < len(arr)` on line 5"
- ❌ BAD: "You have an off-by-one error in your loop"
- ✅ GOOD: "When you access arr[i], what's the largest valid index for an array of length n? Now look at your loop condition—what's the maximum value i can reach?"

For a missing return statement:
- ❌ BAD: "Add `return result` at the end of your function"
- ✅ GOOD: "Your function calculates the answer correctly, but trace through what happens when the function ends. How does the caller receive the computed value?"

For using wrong comparison operator:
- ❌ BAD: "You're using = instead of == for comparison"
- ✅ GOOD: "Look at your if statement. In Python, how do we check if two values are equal versus assigning a value to a variable?"

## Output Format
Respond with ONLY a JSON array of exactly 3 objects, no other text:
[
  {{
    "error_type": "...",
    "buggy_code": "...",
    "bug_explanation": "...",
    "socratic_hint": "..."
  }},
  {{
    "error_type": "...",
    "buggy_code": "...",
    "bug_explanation": "...",
    "socratic_hint": "..."
  }},
  {{
    "error_type": "...",
    "buggy_code": "...",
    "bug_explanation": "...",
    "socratic_hint": "..."
  }}
]
"""


def generate_examples(problem: Dict, max_retries: int = 3) -> List[Dict]:
    """Generate training examples for a single problem."""
    
    # Truncate description if too long
    description = problem['description']
    if len(description) > 3000:
        description = description[:3000] + "\n[Description truncated...]"
    
    prompt = GENERATION_PROMPT.format(
        title=problem['title'],
        difficulty=problem['difficulty'],
        description=description,
        solution=problem['solution']
    )
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            
            # Extract JSON array from response
            import re
            # Try to find JSON array
            json_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', content)
            
            if json_match:
                examples = json.loads(json_match.group())
                
                # Validate we got 3 examples
                if len(examples) < 1:
                    raise ValueError("No examples generated")
                
                # Add problem metadata to each example
                for ex in examples:
                    ex['problem_id'] = problem['id']
                    ex['problem_title'] = problem['title']
                    ex['problem_description'] = problem['description']
                    ex['problem_solution'] = problem['solution']
                    ex['difficulty'] = problem['difficulty']
                    ex['tags'] = problem['tags']
                
                return examples
            else:
                print(f"    Attempt {attempt + 1}: Could not extract JSON, retrying...")
                
        except json.JSONDecodeError as e:
            print(f"    Attempt {attempt + 1}: JSON parse error: {e}")
        except Exception as e:
            print(f"    Attempt {attempt + 1}: Error: {e}")
        
        time.sleep(2)  # Wait before retry
    
    print(f"    Failed to generate examples after {max_retries} attempts")
    return []


def main():
    # Check for API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY not found in environment")
        print("Create a .env file in the scripts/ directory with:")
        print("  ANTHROPIC_API_KEY=your-key-here")
        return
    
    # Load source problems
    input_path = '../data/source_problems.json'
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found. Run step1_prepare_problems.py first.")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        problems = json.load(f)
    
    print(f"Loaded {len(problems)} problems")
    print("Generating training examples using Claude...")
    print("-" * 50)
    
    all_examples = []
    failed_problems = []
    
    for i, problem in enumerate(problems):
        print(f"[{i+1}/{len(problems)}] {problem['title']}")
        
        examples = generate_examples(problem)
        
        if examples:
            all_examples.extend(examples)
            print(f"    ✓ Generated {len(examples)} examples")
        else:
            failed_problems.append(problem['title'])
            print(f"    ✗ Failed")
        
        # Save incrementally (in case of interruption)
        output_path = '../data/generated_examples_raw.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_examples, f, indent=2, ensure_ascii=False)
        
        # Rate limiting - be respectful to the API
        time.sleep(1)
    
    # Final summary
    print("\n" + "=" * 50)
    print("GENERATION COMPLETE")
    print("=" * 50)
    print(f"Total examples generated: {len(all_examples)}")
    print(f"Problems processed: {len(problems) - len(failed_problems)}/{len(problems)}")
    
    if failed_problems:
        print(f"\nFailed problems ({len(failed_problems)}):")
        for title in failed_problems[:10]:
            print(f"  - {title}")
        if len(failed_problems) > 10:
            print(f"  ... and {len(failed_problems) - 10} more")
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
