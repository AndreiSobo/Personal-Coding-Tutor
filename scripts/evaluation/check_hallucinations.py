"""
Hallucination Detection for PACT Model
======================================
This script checks if the model's hints are accurate and address
the actual bug in the student's code.

Metrics:
1. Error Identification Accuracy (EIA) - Does it identify the real bug?
2. Factual Correctness Rate (FCR) - Is the technical content accurate?
3. Consistency Score - Does it give consistent hints for the same input?
"""

import json
import re
import os
from typing import List, Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')


# ========================================
# ERROR IDENTIFICATION ACCURACY
# ========================================

def check_error_identification(
    test_cases: List[Dict],
    responses: List[str],
    use_claude: bool = True
) -> List[Dict]:
    """
    Check if the model correctly identifies the actual bug.
    Uses LLM to evaluate semantic match between hint and actual bug.
    """
    
    CHECK_PROMPT = """A student submitted this buggy code for a coding problem:

```python
{buggy_code}
```

The ACTUAL bug in this code is: {actual_bug}

The AI tutor gave this hint: "{hint}"

Evaluation questions:
1. Does the hint address the ACTUAL bug described above?
2. Does the hint point the student toward the correct issue?
3. Does the hint mention or imply a DIFFERENT problem that doesn't exist?

Respond with ONLY a JSON object:
{{
    "addresses_actual_bug": true or false,
    "points_to_correct_issue": true or false,
    "mentions_nonexistent_problem": true or false,
    "confidence": "high" or "medium" or "low",
    "explanation": "<brief explanation>"
}}"""

    results = []
    
    if use_claude:
        import anthropic
        client = anthropic.Anthropic()
        model = "claude-sonnet-4-20250514"
    else:
        import openai
        client = openai.OpenAI()
        model = "gpt-4o"
    
    for i, (test_case, response) in enumerate(zip(test_cases, responses)):
        print(f"  Checking {i+1}/{len(test_cases)}...")
        
        prompt = CHECK_PROMPT.format(
            buggy_code=test_case.get('buggy_code', ''),
            actual_bug=test_case.get('bug_explanation', ''),
            hint=response
        )
        
        try:
            if use_claude:
                result = client.messages.create(
                    model=model,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = result.content[0].text
            else:
                result = client.chat.completions.create(
                    model=model,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                content = result.choices[0].message.content
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                evaluation = json.loads(json_match.group())
                results.append(evaluation)
            else:
                results.append({"error": "Could not parse response"})
                
        except Exception as e:
            results.append({"error": str(e)})
    
    return results


# ========================================
# FACTUAL CORRECTNESS
# ========================================

def check_factual_correctness(
    responses: List[str],
    use_claude: bool = True
) -> List[Dict]:
    """
    Check if the hints contain factually correct Python information.
    """
    
    CHECK_PROMPT = """Evaluate this Python tutoring hint for technical accuracy:

Hint: "{hint}"

Check for:
1. Incorrect claims about Python syntax
2. Wrong explanations of how Python works
3. Incorrect terminology
4. Misleading debugging advice
5. False statements about data structures/algorithms

Respond with ONLY a JSON object:
{{
    "is_factually_correct": true or false,
    "errors_found": ["error1", "error2"] or [],
    "severity": "none" or "minor" or "major",
    "explanation": "<brief explanation if errors found>"
}}"""

    results = []
    
    if use_claude:
        import anthropic
        client = anthropic.Anthropic()
        model = "claude-sonnet-4-5"
    else:
        import openai
        client = openai.OpenAI()
        model = "gpt-4o"
    
    for i, response in enumerate(responses):
        print(f"  Checking {i+1}/{len(responses)}...")
        
        prompt = CHECK_PROMPT.format(hint=response)
        
        try:
            if use_claude:
                result = client.messages.create(
                    model=model,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = result.content[0].text
            else:
                result = client.chat.completions.create(
                    model=model,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                content = result.choices[0].message.content
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                evaluation = json.loads(json_match.group())
                results.append(evaluation)
            else:
                results.append({"error": "Could not parse response"})
                
        except Exception as e:
            results.append({"error": str(e)})
    
    return results


# ========================================
# CONSISTENCY CHECK
# ========================================

def check_consistency(
    test_cases: List[Dict],
    model_func,  # Function that generates response given a test case
    n_runs: int = 3
) -> List[Dict]:
    """
    Check if the model gives consistent hints for the same input.
    Runs the same prompt multiple times and checks if hints address the same issue.
    
    Note: This requires a function that can call your model.
    """
    
    CONSISTENCY_PROMPT = """These are {n} different hints given by an AI tutor for the SAME coding problem:

{hints}

Do all hints point the student toward the SAME underlying issue/concept?

Respond with ONLY a JSON object:
{{
    "all_consistent": true or false,
    "consistency_score": <0.0 to 1.0>,
    "main_issue_identified": "<what issue most hints address>",
    "outlier_hints": [<indices of hints that differ>] or [],
    "explanation": "<brief explanation>"
}}"""

    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"  Testing consistency for case {i+1}/{len(test_cases)}...")
        
        # Generate multiple responses
        responses = []
        for run in range(n_runs):
            response = model_func(test_case)
            responses.append(response)
        
        # Format hints for evaluation
        hints_text = "\n".join([f"Hint {j+1}: \"{r}\"" for j, r in enumerate(responses)])
        
        prompt = CONSISTENCY_PROMPT.format(n=n_runs, hints=hints_text)
        
        # Use Claude/GPT to evaluate consistency
        try:
            import anthropic
            client = anthropic.Anthropic()
            
            result = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            content = result.content[0].text
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                evaluation = json.loads(json_match.group())
                evaluation['responses'] = responses
                results.append(evaluation)
            else:
                results.append({"error": "Could not parse response", "responses": responses})
                
        except Exception as e:
            results.append({"error": str(e), "responses": responses})
    
    return results


# ========================================
# MAIN
# ========================================

def run_hallucination_check(
    test_cases: List[Dict],
    responses: List[str],
    check_factual: bool = True,
    check_identification: bool = True
):
    """Run full hallucination detection suite."""
    
    print("=" * 60)
    print("HALLUCINATION DETECTION")
    print("=" * 60)
    print(f"Evaluating {len(responses)} responses")
    
    results = {}
    
    # Error identification check
    if check_identification and test_cases:
        print("\n🎯 ERROR IDENTIFICATION ACCURACY")
        print("-" * 40)
        
        id_results = check_error_identification(test_cases, responses)
        valid_results = [r for r in id_results if 'error' not in r]
        
        if valid_results:
            addresses_bug = sum(1 for r in valid_results if r.get('addresses_actual_bug', False))
            hallucinated = sum(1 for r in valid_results if r.get('mentions_nonexistent_problem', False))
            
            eia = (addresses_bug / len(valid_results)) * 100
            hallucination_rate = (hallucinated / len(valid_results)) * 100
            
            print(f"Error Identification Accuracy: {eia:.1f}%  {'✅' if eia >= 85 else '❌'} (target: >= 85%)")
            print(f"Hallucination Rate:            {hallucination_rate:.1f}%  {'✅' if hallucination_rate <= 10 else '❌'} (target: <= 10%)")
            
            results['eia'] = eia
            results['hallucination_rate'] = hallucination_rate
            results['id_results'] = id_results
    
    # Factual correctness check
    if check_factual:
        print("\n📚 FACTUAL CORRECTNESS")
        print("-" * 40)
        
        fact_results = check_factual_correctness(responses)
        valid_results = [r for r in fact_results if 'error' not in r]
        
        if valid_results:
            correct = sum(1 for r in valid_results if r.get('is_factually_correct', False))
            major_errors = sum(1 for r in valid_results if r.get('severity') == 'major')
            
            fcr = (correct / len(valid_results)) * 100
            
            print(f"Factual Correctness Rate: {fcr:.1f}%  {'✅' if fcr >= 95 else '❌'} (target: >= 95%)")
            print(f"Major Errors Found:       {major_errors}  {'✅' if major_errors == 0 else '❌'}")
            
            results['fcr'] = fcr
            results['major_errors'] = major_errors
            results['fact_results'] = fact_results
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if results.get('eia', 0) >= 85 and results.get('fcr', 0) >= 95:
        print("✅ Model passes hallucination checks!")
    else:
        print("⚠️  Model may have hallucination issues:")
        if results.get('eia', 0) < 85:
            print(f"   - Improve error identification (currently {results.get('eia', 0):.1f}%)")
        if results.get('fcr', 0) < 95:
            print(f"   - Check factual accuracy (currently {results.get('fcr', 0):.1f}%)")
    
    return results


def main():
    """Main function."""
    
    # Check for test data
    test_responses_path = "../data/test_responses.json"
    test_cases_path = "../data/test_cases.json"
    
    if os.path.exists(test_responses_path) and os.path.exists(test_cases_path):
        print(f"Loading test data...")
        
        with open(test_responses_path, 'r') as f:
            responses = json.load(f)
        
        with open(test_cases_path, 'r') as f:
            test_cases = json.load(f)
        
        run_hallucination_check(test_cases, responses)
        
    else:
        print("No test data found.")
        print("\nTo use this script:")
        print("1. Save test cases to data/test_cases.json")
        print("   Format: [{\"buggy_code\": \"...\", \"bug_explanation\": \"...\"}, ...]")
        print("2. Save model responses to data/test_responses.json")
        print("3. Run this script")


if __name__ == "__main__":
    main()
