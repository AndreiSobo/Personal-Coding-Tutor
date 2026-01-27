"""
Step 3: Validate Examples using GPT-4
======================================
This script uses GPT-4 to validate the generated training examples.
Using a different model for validation helps catch systematic errors.

Input: data/generated_examples_raw.json
Output: data/examples_passed.json, data/examples_needs_revision.json, data/examples_rejected.json
"""

import openai
import json
import time
import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

# Initialize OpenAI client
client = openai.OpenAI()

VALIDATION_PROMPT = """
You are a quality assurance checker for a Socratic coding tutor training dataset.

## Training Example to Validate

**Problem:** {problem_title}
**Difficulty:** {difficulty}

**Buggy Code:**
```python
{buggy_code}
```

**Claimed Error Type:** {error_type}
**Bug Explanation:** {bug_explanation}

**Socratic Hint:** "{socratic_hint}"

## Validation Criteria

Evaluate this training example on each criterion:

1. **buggy_code_is_realistic**: Is this a mistake a real student would plausibly make? (not artificially stupid or random)

2. **buggy_code_is_actually_buggy**: Does the code ACTUALLY fail or produce wrong output for at least one test case? 
   - Trace through the code mentally to verify it fails
   - Don't accept "suboptimal" code that still works correctly

3. **hint_is_socratic**: Does the hint guide through questions/suggestions rather than telling the answer directly?

4. **hint_contains_no_code**: Is the hint completely free of:
   - Code snippets or syntax (brackets, quotes, operators)
   - Variable names from the code/solution (e.g., 'stack', 'nums', 'left', 'i')
   - Specific function names from the code
   - Code-like input examples (e.g., [1,2,3], "abc")
   
   ALLOWED: General terms like "the loop", "the array", "the condition", "first element"
   NOT ALLOWED: Specific identifiers like "stack", "nums", "target"

5. **hint_avoids_direct_fix**: Does the hint avoid phrases like:
   - "change X to Y"
   - "you need to"
   - "you should"
   - "add a check for"
   - "the problem is"
   - "your error is"

6. **hint_is_helpful**: Would this hint actually help a stuck student make progress?

7. **hint_matches_bug**: Does the hint address the actual bug in the code (not a different issue)?

## Response Format
Respond with ONLY a JSON object, no other text:
{{
  "buggy_code_is_realistic": true or false,
  "buggy_code_is_actually_buggy": true or false,
  "hint_is_socratic": true or false,
  "hint_contains_no_code": true or false,
  "hint_avoids_direct_fix": true or false,
  "hint_is_helpful": true or false,
  "hint_matches_bug": true or false,
  "overall_quality": "pass" or "needs_revision" or "reject",
  "issues": ["issue1", "issue2"] or [],
  "suggested_improvement": "optional suggestion if needs_revision"
}}

Guidelines for overall_quality:
- "pass": All criteria are true
- "needs_revision": Most criteria true, but hint needs improvement (fixable with minor changes)
- "reject": Fundamental problems - buggy code isn't actually buggy OR hint reveals the solution OR multiple severe violations
"""


def validate_example(example: Dict, max_retries: int = 3) -> Dict:
    """Validate a single training example using GPT-5."""
    
    prompt = VALIDATION_PROMPT.format(
        problem_title=example['problem_title'],
        difficulty=example['difficulty'],
        buggy_code=example['buggy_code'],
        error_type=example['error_type'],
        bug_explanation=example['bug_explanation'],
        socratic_hint=example['socratic_hint']
    )
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-5.2",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=500,
                temperature=0  # Deterministic for consistency
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            
            if json_match:
                validation = json.loads(json_match.group())
                return validation
            else:
                print(f"      Attempt {attempt + 1}: Could not extract JSON")
                
        except json.JSONDecodeError as e:
            print(f"      Attempt {attempt + 1}: JSON parse error: {e}")
        except Exception as e:
            print(f"      Attempt {attempt + 1}: Error: {e}")
        
        time.sleep(1)
    
    return {
        "overall_quality": "error",
        "issues": ["Validation failed after multiple attempts"]
    }


def main():
    # Check for API key
    if not os.environ.get('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in environment")
        print("Create a .env file in the scripts/ directory with:")
        print("  OPENAI_API_KEY=your-key-here")
        return
    
    # Load generated examples
    input_path = '../data/generated_examples_raw.json'
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found. Run step2_generate_examples.py first.")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        examples = json.load(f)
    
    print(f"Loaded {len(examples)} examples to validate")
    print("Validating using GPT-4...")
    print("-" * 50)
    
    validated_examples = []
    passed = []
    needs_revision = []
    rejected = []
    errors = []
    
    for i, example in enumerate(examples):
        print(f"[{i+1}/{len(examples)}] {example['problem_title']} - {example['error_type']}")
        
        validation = validate_example(example)
        example['validation'] = validation
        validated_examples.append(example)
        
        quality = validation.get('overall_quality', 'error')
        
        if quality == 'pass':
            passed.append(example)
            print(f"    ✓ Passed")
        elif quality == 'needs_revision':
            needs_revision.append(example)
            issues = validation.get('issues', [])
            print(f"    ⚠ Needs revision: {', '.join(issues[:2])}")
        elif quality == 'reject':
            rejected.append(example)
            issues = validation.get('issues', [])
            print(f"    ✗ Rejected: {', '.join(issues[:2])}")
        else:
            errors.append(example)
            print(f"    ? Validation error")
        
        # Save incrementally
        with open('../data/validated_examples.json', 'w', encoding='utf-8') as f:
            json.dump(validated_examples, f, indent=2, ensure_ascii=False)
        
        # Rate limiting
        time.sleep(0.5)
    
    # Save categorized results
    with open('../data/examples_passed.json', 'w', encoding='utf-8') as f:
        json.dump(passed, f, indent=2, ensure_ascii=False)
    
    with open('../data/examples_needs_revision.json', 'w', encoding='utf-8') as f:
        json.dump(needs_revision, f, indent=2, ensure_ascii=False)
    
    with open('../data/examples_rejected.json', 'w', encoding='utf-8') as f:
        json.dump(rejected, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION COMPLETE")
    print("=" * 50)
    total = len(examples)
    print(f"Total validated: {total}")
    print(f"  ✓ Passed:         {len(passed):4d} ({100*len(passed)/total:.1f}%)")
    print(f"  ⚠ Needs revision: {len(needs_revision):4d} ({100*len(needs_revision)/total:.1f}%)")
    print(f"  ✗ Rejected:       {len(rejected):4d} ({100*len(rejected)/total:.1f}%)")
    print(f"  ? Errors:         {len(errors):4d} ({100*len(errors)/total:.1f}%)")
    
    print("\nOutput files:")
    print("  - data/examples_passed.json")
    print("  - data/examples_needs_revision.json")
    print("  - data/examples_rejected.json")
    
    # Show common issues
    all_issues = []
    for ex in needs_revision + rejected:
        all_issues.extend(ex.get('validation', {}).get('issues', []))
    
    if all_issues:
        from collections import Counter
        issue_counts = Counter(all_issues)
        print("\nMost common issues:")
        for issue, count in issue_counts.most_common(5):
            print(f"  - {issue}: {count}")


if __name__ == "__main__":
    main()
