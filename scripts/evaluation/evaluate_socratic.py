"""
Evaluate Socratic Quality of Fine-Tuned Model
=============================================
This script evaluates the fine-tuned PACT model on key metrics:
1. Code Leakage Rate (CLR) - Does it give away code?
2. Guiding Question Rate (GQR) - Does it ask questions?
3. Direct Answer Rate (DAR) - Does it reveal fixes directly?
4. Pedagogical Score - LLM-as-Judge evaluation

Input: Test examples + access to fine-tuned model
Output: Evaluation report with scores
"""

import json
import re
import os
from typing import List, Dict, Tuple
from collections import Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')


# ========================================
# REGEX-BASED METRICS (Fast, No API)
# ========================================

def calculate_code_leakage_rate(responses: List[str]) -> Tuple[float, List[int]]:
    """
    Calculate percentage of responses containing executable code.
    Target: < 5%
    
    Returns: (percentage, list of indices with leakage)
    """
    code_patterns = [
        r'```python[\s\S]*?```',      # Markdown Python blocks
        r'```[\s\S]*?```',             # Any code blocks
        r'def \w+\s*\([^)]*\)\s*:',    # Function definitions
        r'for \w+ in .+:',             # For loops
        r'while .+:',                   # While loops
        r'if .+:[\s\n]+\s{2,}\w',      # If statements with indented body
        r'return \[.+\]',              # Return with list
        r'\w+\s*=\s*\[.+\]',           # List assignment
        r'`[^`]+\(`',                  # Inline function calls
    ]
    
    leaky_indices = []
    for i, response in enumerate(responses):
        for pattern in code_patterns:
            if re.search(pattern, response, re.MULTILINE):
                leaky_indices.append(i)
                break
    
    rate = (len(leaky_indices) / len(responses)) * 100 if responses else 0
    return rate, leaky_indices


def calculate_guiding_question_rate(responses: List[str]) -> Tuple[float, List[int]]:
    """
    Calculate percentage of responses containing guiding questions.
    Target: > 70%
    
    Returns: (percentage, list of indices WITH questions)
    """
    question_patterns = [
        r'\?',                          # Any question mark
        r'what happens when',
        r'have you considered',
        r'what do you think',
        r'can you explain',
        r'why might',
        r'what would happen if',
        r'how does',
        r'what is the',
        r'when would',
        r'where does',
    ]
    
    question_indices = []
    for i, response in enumerate(responses):
        response_lower = response.lower()
        if any(re.search(p, response_lower) for p in question_patterns):
            question_indices.append(i)
    
    rate = (len(question_indices) / len(responses)) * 100 if responses else 0
    return rate, question_indices


def calculate_direct_answer_rate(responses: List[str]) -> Tuple[float, List[int]]:
    """
    Calculate percentage of responses that directly reveal the solution.
    Target: < 10%
    
    Returns: (percentage, list of indices with direct answers)
    """
    direct_patterns = [
        r'\bchange\s+.+\s+to\s+',
        r'\breplace\s+.+\s+with\s+',
        r'\bthe\s+(?:answer|solution|fix)\s+is\b',
        r'\byou\s+(?:need|should|must)\s+(?:to\s+)?(?:use|change|add|remove|replace)',
        r'\bjust\s+(?:add|change|use|remove|put)\b',
        r'\bthe\s+(?:correct|right|proper)\s+(?:way|approach|solution|code)\b',
        r'\bhere\'s\s+(?:the|a|how)\b',
        r'\bthe\s+(?:bug|error|problem|issue)\s+is\s+(?:that|in|on|at)\b',
        r'\byour\s+(?:error|mistake|bug)\s+is\b',
    ]
    
    direct_indices = []
    for i, response in enumerate(responses):
        response_lower = response.lower()
        if any(re.search(p, response_lower) for p in direct_patterns):
            direct_indices.append(i)
    
    rate = (len(direct_indices) / len(responses)) * 100 if responses else 0
    return rate, direct_indices


# ========================================
# LLM-AS-JUDGE EVALUATION
# ========================================

def evaluate_with_llm_judge(
    test_cases: List[Dict],
    responses: List[str],
    use_claude: bool = True
) -> List[Dict]:
    """
    Use an LLM to evaluate pedagogical quality.
    
    Returns list of evaluation results with scores.
    """
    
    JUDGE_PROMPT = """You are evaluating an AI coding tutor's response for pedagogical quality.

CONTEXT:
- Problem: {problem}
- Student's buggy code:
```python
{code}
```
- The actual bug: {bug}

TUTOR'S RESPONSE:
"{response}"

EVALUATION CRITERIA (rate 1-5):

1. SOCRATIC_QUALITY: Does it guide through questions rather than tell?
   5 = Pure Socratic questioning, no direct answers
   3 = Mix of questions and hints
   1 = Directly tells the answer

2. HELPFULNESS: Would this actually help a stuck student?
   5 = Clear, actionable guidance
   3 = Somewhat helpful
   1 = Confusing or unhelpful

3. ACCURACY: Is the guidance technically correct?
   5 = Completely accurate
   3 = Mostly accurate
   1 = Contains errors

4. CODE_AVOIDANCE: Does it avoid giving code?
   5 = No code at all
   3 = Minor code-like elements
   1 = Contains code solutions

Respond with ONLY a JSON object:
{{"socratic": <1-5>, "helpful": <1-5>, "accurate": <1-5>, "code_avoidance": <1-5>, "reasoning": "<brief explanation>"}}"""

    results = []
    
    if use_claude:
        import anthropic
        client = anthropic.Anthropic()
        model = "claude-sonnet-4-5"
    else:
        import openai
        client = openai.OpenAI()
        model = "gpt-5.2"
    
    for i, (test_case, response) in enumerate(zip(test_cases, responses)):
        print(f"  Evaluating {i+1}/{len(test_cases)}...")
        
        prompt = JUDGE_PROMPT.format(
            problem=test_case.get('problem_title', 'Unknown'),
            code=test_case.get('buggy_code', ''),
            bug=test_case.get('bug_explanation', ''),
            response=response
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
            
            # Parse JSON
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
# MAIN EVALUATION
# ========================================

def run_evaluation(responses: List[str], test_cases: List[Dict] = None, use_llm_judge: bool = False):
    """Run full evaluation suite."""
    
    print("=" * 60)
    print("PACT MODEL EVALUATION")
    print("=" * 60)
    print(f"Evaluating {len(responses)} responses")
    print("-" * 60)
    
    # Regex-based metrics
    print("\n📊 AUTOMATED METRICS")
    print("-" * 40)
    
    clr, leaky = calculate_code_leakage_rate(responses)
    gqr, questions = calculate_guiding_question_rate(responses)
    dar, direct = calculate_direct_answer_rate(responses)
    
    print(f"Code Leakage Rate (CLR):     {clr:5.1f}%  {'✅' if clr < 5 else '❌'} (target: < 5%)")
    print(f"Guiding Question Rate (GQR): {gqr:5.1f}%  {'✅' if gqr > 70 else '❌'} (target: > 70%)")
    print(f"Direct Answer Rate (DAR):    {dar:5.1f}%  {'✅' if dar < 10 else '❌'} (target: < 10%)")
    
    # LLM-as-Judge
    if use_llm_judge and test_cases:
        print("\n🤖 LLM-AS-JUDGE EVALUATION")
        print("-" * 40)
        print("(Using Claude sonnet 4.5/GPT-5.2 to evaluate pedagogical quality)")
        
        judge_results = evaluate_with_llm_judge(test_cases, responses)
        
        # Calculate averages
        valid_results = [r for r in judge_results if 'error' not in r]
        if valid_results:
            avg_socratic = sum(r.get('socratic', 0) for r in valid_results) / len(valid_results)
            avg_helpful = sum(r.get('helpful', 0) for r in valid_results) / len(valid_results)
            avg_accurate = sum(r.get('accurate', 0) for r in valid_results) / len(valid_results)
            avg_code_avoid = sum(r.get('code_avoidance', 0) for r in valid_results) / len(valid_results)
            
            print(f"Socratic Quality:   {avg_socratic:.2f}/5  {'✅' if avg_socratic >= 4 else '⚠️'}")
            print(f"Helpfulness:        {avg_helpful:.2f}/5  {'✅' if avg_helpful >= 4 else '⚠️'}")
            print(f"Accuracy:           {avg_accurate:.2f}/5  {'✅' if avg_accurate >= 4 else '⚠️'}")
            print(f"Code Avoidance:     {avg_code_avoid:.2f}/5  {'✅' if avg_code_avoid >= 4 else '⚠️'}")
            
            overall = (avg_socratic + avg_helpful + avg_accurate + avg_code_avoid) / 4
            print(f"\nOverall Score:      {overall:.2f}/5")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    automated_pass = clr < 5 and gqr > 70 and dar < 10
    
    if automated_pass:
        print("✅ Model passes automated metrics!")
    else:
        print("⚠️  Model needs improvement:")
        if clr >= 5:
            print(f"   - Reduce code leakage (currently {clr:.1f}%)")
        if gqr <= 70:
            print(f"   - Increase use of questions (currently {gqr:.1f}%)")
        if dar >= 10:
            print(f"   - Reduce direct answers (currently {dar:.1f}%)")
    
    # Show examples of issues
    if leaky:
        print(f"\nExamples with code leakage (indices): {leaky[:5]}")
    if direct:
        print(f"Examples with direct answers (indices): {direct[:5]}")
    
    return {
        "code_leakage_rate": clr,
        "guiding_question_rate": gqr,
        "direct_answer_rate": dar,
        "leaky_indices": leaky,
        "direct_indices": direct
    }


def main():
    """
    Main function - load test data and run evaluation.
    
    To evaluate your model:
    1. Generate responses from your model for test cases
    2. Save responses to a JSON file
    3. Run this script
    """
    
    # Check for test data
    test_responses_path = "../data/test_responses.json"
    test_cases_path = "../data/test_cases.json"
    
    if os.path.exists(test_responses_path):
        print(f"Loading test responses from {test_responses_path}")
        with open(test_responses_path, 'r') as f:
            responses = json.load(f)
        
        test_cases = None
        if os.path.exists(test_cases_path):
            with open(test_cases_path, 'r') as f:
                test_cases = json.load(f)
        
        run_evaluation(responses, test_cases, use_llm_judge=False)
        
    else:
        print("No test data found.")
        print("\nTo use this script:")
        print("1. Generate responses from your fine-tuned model")
        print("2. Save them to data/test_responses.json as a JSON array")
        print("3. Optionally save test cases to data/test_cases.json")
        print("4. Run this script again")
        
        # Run with example data for demonstration
        print("\n" + "-" * 60)
        print("Running with example responses for demonstration...")
        print("-" * 60)
        
        example_responses = [
            "When you access arr[i], what's the largest valid index for an array of length n? Now look at your loop condition—what's the maximum value i can reach?",
            "Your function calculates something, but trace through what happens when it ends. How does the caller receive the computed value?",
            "Look at your if statement. In Python, how do we check if two values are equal versus assigning a value?",
            "You need to change i <= len(arr) to i < len(arr)",  # Bad example - direct answer
            "Think about what happens when you try to access an index that doesn't exist. What error would Python give you?",
        ]
        
        run_evaluation(example_responses)


if __name__ == "__main__":
    main()
