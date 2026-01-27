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

## CRITICAL: BUGGY CODE MUST ACTUALLY FAIL
The buggy code MUST produce wrong output or crash for at least one test case.
- ✅ GOOD: Code that gives wrong answer for some inputs
- ❌ BAD: Code that works but is "suboptimal" or "not elegant"
- ❌ BAD: Edge cases that the code actually handles correctly

TEST YOUR BUGS: Mentally trace through the buggy code with test cases to confirm it fails.

## CRITICAL RULES FOR SOCRATIC HINTS

The hint MUST:
✅ Ask a guiding question OR point toward the problem area using general concepts
✅ Be encouraging and supportive in tone
✅ Help the student discover the issue themselves
✅ Use ONLY general programming concepts (loops, conditions, arrays, etc.)

The hint must ABSOLUTELY NEVER:
❌ Contain ANY code snippets or syntax (no brackets, quotes, semicolons, etc.)
❌ Mention ANY variable names from the code or solution
❌ Mention specific function names from the code
❌ Reference specific data structure names used in the code (like 'stack', 'dict', 'left', 'right')
❌ Use directive phrases like "you should", "you need to", "the solution is", "change X to Y"
❌ Directly state what's wrong (e.g., "your loop condition is wrong")
❌ Include example inputs with programming syntax like [1,2,3] or "abc"

## SAFE Language for Hints
You MAY use:
✅ General concepts: "the loop", "the condition", "the comparison", "the data structure"
✅ General terms: "first element", "last position", "the current value", "the input"
✅ Questions: "What happens when...", "Consider the case where...", "How does... behave..."
✅ Conceptual guidance: "Think about edge cases", "Consider the order of operations"

You must NOT use:
❌ Specific identifiers from code: "stack", "nums", "left", "target", "strs"
❌ Code-like examples: "[1,2,3]", "nums[i]", "s == ''", "for i in range"

## Examples of GOOD vs BAD hints

For an off-by-one error in array access:
- ❌ BAD: "When you access arr[i], what's the largest valid index for an array of length n?"
  (Uses variable names 'arr', 'i', 'n')
- ❌ BAD: "Look at your loop condition with i <= len(arr)"
  (Uses variable names and code syntax)
- ✅ GOOD: "When accessing elements by index, what's the relationship between the array length and the largest valid index? How does your loop boundary compare to this?"

For a missing return statement:
- ❌ BAD: "Your function calculates the answer correctly, but trace through what happens when the function ends. How does the caller receive the computed value?"
  (Mentions 'the computed value' which hints at the fix)
- ✅ GOOD: "You're doing the calculation, but trace through what happens at the end of your function. What value does the calling code receive?"

For using = instead of == in comparison:
- ❌ BAD: "Look at your if statement. In Python, how do we check if two values are equal versus assigning a value to a variable?"
  (Too close to stating the answer)
- ✅ GOOD: "In your conditional check, what's the difference between assignment and comparison in Python? Which operation are you performing?"

For wrong algorithm (nested loops when hashmap needed):
- ❌ BAD: "Your solution uses nested loops. Could a hash table make this O(n)?"
  (Directly suggests the fix)
- ✅ GOOD: "Your approach checks every pair of elements. In problems involving lookups, what data structure allows you to check if something exists in constant time?"

For edge case (empty input):
- ❌ BAD: "What happens when strs = []? Add a check at the start."
  (Uses variable name and directive language)
- ✅ GOOD: "Consider what happens when the input is empty. Does your code handle this case before processing begins?"

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
    if len(description) > 5000:
        description = description[:5000] + "\n[Description truncated...]"
    
    prompt = GENERATION_PROMPT.format(
        title=problem['title'],
        difficulty=problem['difficulty'],
        description=description,
        solution=problem['solution']
    )
    
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            if not response.content:
                raise ValueError("Empty response from Claude API")
            
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
        return
    
    # Load source problems
    input_path = '../data/source_problems.json'
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found. Ensure that source_problems.json exists.")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        problems = json.load(f)
    
    print(f"Loaded {len(problems)} problems")
    print("Generating training examples using Claude...")
    print("-" * 50)
    
    all_examples = []
    failed_problems = []
    
    for i, problem in enumerate(problems[:10]):
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
