"""
PACT Model Evaluation - Comprehensive LLM-as-Judge
===================================================
Evaluates fine-tuned model on 5 key metrics using Claude Sonnet 4.5

Metrics:
1. Code Leakage Rate (CLR) - Percentage giving code solutions
2. Direct Answer Rate (DAR) - Percentage directly revealing fixes
3. Socratic Quality (SQ) - Quality of guided questioning approach
4. Helpfulness (H) - Whether guidance actually helps students
5. Factual Correctness (FC) - Technical accuracy of hints

"""

import json
import re
import os
from typing import List, Dict, Tuple
from collections import Counter
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv('../.env')


# ========================================
# EVALUATION PROMPTS
# ========================================

EVALUATION_PROMPT = """You are evaluating an AI coding tutor's response to a student who submitted buggy code.

STUDENT'S BUGGY CODE:
```python
{buggy_code}
```

TUTOR'S RESPONSE:
"{response}"

Evaluate the response on these 5 criteria:

1. CODE_LEAKAGE (Yes/No): Does the response contain executable code that solves the problem?
   - "Yes" if it includes ```python blocks, function definitions, or multi-line code snippets
   - "No" if it only mentions concepts or asks questions with brief code references

2. DIRECT_ANSWER (Yes/No): Does it directly tell the student the fix?
   - "Yes" if it explicitly says "change X to Y", "the bug is Z", "use method W"
   - "No" if it guides toward discovery through questions or hints

3. SOCRATIC_QUALITY (1-5): How well does it guide through questions?
   - 5: Pure Socratic - only guiding questions, no direct answers
   - 4: Mostly questions with minimal hints
   - 3: Mix of questions and direct hints
   - 2: Mostly direct hints with some questions
   - 1: All direct answers, no questions

4. HELPFULNESS (1-5): Would this actually help a stuck student make progress?
   - 5: Clear, actionable guidance that leads to understanding
   - 4: Helpful but could be clearer
   - 3: Somewhat helpful but vague
   - 2: Confusing or misleading
   - 1: Unhelpful or wrong direction

5. FACTUAL_CORRECTNESS (Yes/No): Is the technical content accurate?
   - "Yes" if all Python facts, syntax explanations, and debugging advice are correct
   - "No" if it contains errors about how Python works, wrong terminology, or incorrect claims

Respond with ONLY a JSON object (no markdown, no explanation):
{{
    "code_leakage": "Yes" or "No",
    "direct_answer": "Yes" or "No",
    "socratic_quality": 1-5,
    "helpfulness": 1-5,
    "factual_correctness": "Yes" or "No",
    "brief_reasoning": "<one sentence explaining key observations>"
}}"""


# ========================================
# EVALUATION FUNCTION
# ========================================

def evaluate_responses(
    test_cases: List[Dict],
    responses: List[str],
    use_claude: bool = True
) -> List[Dict]:
    """
    Evaluate all responses using LLM-as-judge.
    
    Args:
        test_cases: List of test case dicts with 'buggy_code' field
        responses: List of model responses to evaluate
        use_claude: If True, use Claude Sonnet 4.5; else GPT-4o
    
    Returns:
        List of evaluation results
    """
    
    if use_claude:
        client = anthropic.Anthropic()
        model = "claude-sonnet-4-20250514"
    else:
        # implement chatgpt 5.2, as I was happy with its previous findings
        print("implementing another model")
        
    
    results = []
    
    print(f"\n{'='*60}")
    print(f"EVALUATING {len(responses)} RESPONSES")
    print(f"{'='*60}")
    print(f"Using: {model}")
    print()
    
    for i, (test_case, response) in enumerate(zip(test_cases, responses)):
        print(f"  [{i+1}/{len(responses)}] Evaluating...", end=" ", flush=True)
        
        # Extract buggy code
        buggy_code = test_case.get('buggy_code', '')
        if not buggy_code:
            # Try to extract from full_user_message
            user_msg = test_case.get('full_user_message', '')
            code_match = re.search(r'```python\s*\n(.*?)\n```', user_msg, re.DOTALL)
            buggy_code = code_match.group(1) if code_match else 'N/A'
        
        prompt = EVALUATION_PROMPT.format(
            buggy_code=buggy_code,
            response=response
        )
        
        try:
            if use_claude:
                result = client.messages.create(
                    model=model,
                    max_tokens=400,
                    temperature=0,  # Deterministic for evaluation
                    messages=[{"role": "user", "content": prompt}]
                )
                content = result.content[0].text
            else:
                result = client.chat.completions.create(
                    model=model,
                    max_tokens=400,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = result.choices[0].message.content
            
            # Parse JSON response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                evaluation = json.loads(json_match.group())
                results.append(evaluation)
                print("✓")
            else:
                results.append({"error": "Could not parse JSON"})
                print("✗ (parse error)")
                
        except Exception as e:
            results.append({"error": str(e)})
            print(f"✗ ({type(e).__name__})")
    
    return results


# ========================================
# METRICS CALCULATION
# ========================================

def calculate_metrics(eval_results: List[Dict]) -> Dict:
    """Calculate aggregate metrics from evaluation results."""
    
    valid_results = [r for r in eval_results if 'error' not in r]
    n = len(valid_results)
    
    if n == 0:
        return {"error": "No valid evaluation results"}
    
    # Binary metrics (percentage)
    code_leakage_rate = (sum(1 for r in valid_results if r.get('code_leakage') == 'Yes') / n) * 100
    direct_answer_rate = (sum(1 for r in valid_results if r.get('direct_answer') == 'Yes') / n) * 100
    factual_correctness_rate = (sum(1 for r in valid_results if r.get('factual_correctness') == 'Yes') / n) * 100
    
    # Scaled metrics (average 1-5)
    socratic_scores = [r.get('socratic_quality', 0) for r in valid_results]
    helpfulness_scores = [r.get('helpfulness', 0) for r in valid_results]
    
    avg_socratic = sum(socratic_scores) / n
    avg_helpfulness = sum(helpfulness_scores) / n
    
    return {
        "code_leakage_rate": code_leakage_rate,
        "direct_answer_rate": direct_answer_rate,
        "factual_correctness_rate": factual_correctness_rate,
        "socratic_quality_avg": avg_socratic,
        "helpfulness_avg": avg_helpfulness,
        "total_evaluated": n,
        "errors": len(eval_results) - n
    }


# ========================================
# RESULTS DISPLAY
# ========================================

def display_results(metrics: Dict, eval_results: List[Dict]):
    """Display evaluation results in a clear format."""
    
    print(f"\n{'='*60}")
    print("EVALUATION RESULTS")
    print(f"{'='*60}\n")
    
    # Binary metrics
    print("📊 BINARY METRICS (Lower is Better)")
    print("-" * 60)
    
    clr = metrics['code_leakage_rate']
    print(f"Code Leakage Rate (CLR):     {clr:5.1f}%  {'✅' if clr < 5 else '❌ FAIL'} (target: <5%)")
    
    dar = metrics['direct_answer_rate']
    print(f"Direct Answer Rate (DAR):    {dar:5.1f}%  {'✅' if dar < 10 else '❌ FAIL'} (target: <10%)")
    
    fcr = metrics['factual_correctness_rate']
    print(f"Factual Correctness Rate:    {fcr:5.1f}%  {'✅' if fcr > 95 else '❌ FAIL'} (target: >95%)")
    
    # Scaled metrics
    print(f"\n⭐ QUALITY METRICS (Higher is Better)")
    print("-" * 60)
    
    sq = metrics['socratic_quality_avg']
    print(f"Socratic Quality (1-5):      {sq:5.2f}  {'✅' if sq >= 4.0 else '❌ FAIL'} (target: ≥4.0)")
    
    h = metrics['helpfulness_avg']
    print(f"Helpfulness (1-5):           {h:5.2f}  {'✅' if h >= 4.0 else '❌ FAIL'} (target: ≥4.0)")
    
    # Overall assessment
    print(f"\n{'='*60}")
    print("OVERALL ASSESSMENT")
    print(f"{'='*60}")
    
    passed = (
        clr < 5 and 
        dar < 10 and 
        fcr > 95 and 
        sq >= 4.0 and 
        h >= 4.0
    )
    
    if passed:
        print("✅ MODEL PASSES ALL EVALUATION CRITERIA!")
        print("   Ready for deployment and report writeup.")
    else:
        print("⚠️  MODEL NEEDS IMPROVEMENT:")
        if clr >= 5:
            print(f"   • Reduce code leakage (currently {clr:.1f}%)")
        if dar >= 10:
            print(f"   • Reduce direct answers (currently {dar:.1f}%)")
        if fcr <= 95:
            print(f"   • Improve factual accuracy (currently {fcr:.1f}%)")
        if sq < 4.0:
            print(f"   • Improve Socratic questioning (currently {sq:.2f}/5)")
        if h < 4.0:
            print(f"   • Improve helpfulness (currently {h:.2f}/5)")
    
    # Show error count
    if metrics.get('errors', 0) > 0:
        print(f"\n⚠️  {metrics['errors']} evaluation(s) failed due to errors")
    
    print()


# ========================================
# MAIN
# ========================================

def main():
    """Main evaluation function."""
    
    # Load test data
    test_cases_path = "../data/test_cases.json"
    test_responses_path = "../data/test_responses.json"
    
    if not os.path.exists(test_cases_path):
        print(f"❌ Error: {test_cases_path} not found")
        print("\nRun generate_test_cases.py first to create test cases.")
        return
    
    if not os.path.exists(test_responses_path):
        print(f"❌ Error: {test_responses_path} not found")
        print("\nRun generate_test_responses.py first to generate model responses.")
        return
    
    print("Loading test data...")
    with open(test_cases_path, 'r') as f:
        test_cases = json.load(f)
    
    with open(test_responses_path, 'r') as f:
        responses = json.load(f)
    
    if len(test_cases) != len(responses):
        print(f"⚠️  Warning: {len(test_cases)} test cases but {len(responses)} responses")
        # Use minimum length
        n = min(len(test_cases), len(responses))
        test_cases = test_cases[:n]
        responses = responses[:n]
    
    # Run evaluation
    eval_results = evaluate_responses(test_cases, responses, use_claude=True)
    
    # Calculate metrics
    metrics = calculate_metrics(eval_results)
    
    # Display results
    display_results(metrics, eval_results)
    
    # Save detailed results
    output_path = "../data/evaluation_results.json"
    output = {
        "metrics": metrics,
        "detailed_results": eval_results
    }
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"💾 Detailed results saved to: {output_path}")


if __name__ == "__main__":
    main()