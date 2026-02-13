import json
import re
import os
from typing import Dict, List

from dotenv import load_dotenv
import openai

# Load environment variables (relative to this script)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ========================================
# CONFIGURATION
# ========================================

TEST_CASES_PATH = "../data/test_cases.json"
# Ensure this matches the output file from your generate script
RESPONSES_PATH = "../data/test_responses_comparison.json"
RESULTS_PATH = "../data/evaluation_results_comparison.json"

# Model to use for evaluation
OPENAI_MODEL = "gpt-5.2"

EVALUATION_PROMPT = """You are evaluating an AI coding tutor's response to a student who submitted buggy code.

STUDENT'S BUGGY CODE:
```python
{buggy_code}
```

TUTOR'S RESPONSE:
"{response}"

Evaluate the response on these 5 criteria:

CODE_LEAKAGE (Yes/No): Does the response contain executable code that solves the problem?

"Yes" if it includes python blocks, function definitions, or corrected logic.

"No" if it only mentions concepts, variable names, or asks questions.

DIRECT_ANSWER (Yes/No): Does it directly tell the student the fix?

"Yes" if it says "change X to Y" or "the bug is Z".

"No" if it guides toward discovery.

SOCRATIC_QUALITY (1-5): How well does it guide through questions?

5: Pure Socratic (questions only)

1: Lecture/Direct Answer

HELPFULNESS (1-5): Would this actually help a stuck student?

5: Clear, actionable guidance

1: Confusing/Wrong

FACTUAL_CORRECTNESS (Yes/No): Is the technical content accurate?

Respond with ONLY a JSON object:
{{
"code_leakage": "Yes" or "No",
"direct_answer": "Yes" or "No",
"socratic_quality": 1-5,
"helpfulness": 1-5,
"factual_correctness": "Yes" or "No"
}}"""


def evaluate_single_response(client, buggy_code: str, response: str) -> Dict:
    """Send a single request to the OpenAI client and return parsed JSON result.

    If parsing fails, returns an object with an "error" key.
    """
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=400,
            temperature=0,  # deterministic for evaluation
            messages=[
                {
                    "role": "user",
                    "content": EVALUATION_PROMPT.format(buggy_code=buggy_code, response=response),
                }
            ],
        )

        content = completion.choices[0].message.content

        # Robust JSON parsing: extract first {...} block
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json.loads(json_match.group())

        return {"error": "Parse Error", "raw": content}
    except Exception as e:
        return {"error": str(e)}


def calculate_metrics(results: List[Dict]) -> Dict:
    """Calculate aggregate metrics from individual evaluation results."""
    valid = [r for r in results if "error" not in r]
    n = len(valid)
    if n == 0:
        return {}

    return {
        "CLR": (sum(1 for r in valid if r.get("code_leakage") == "Yes") / n) * 100,
        "DAR": (sum(1 for r in valid if r.get("direct_answer") == "Yes") / n) * 100,
        "FCR": (sum(1 for r in valid if r.get("factual_correctness") == "Yes") / n) * 100,
        "SQ": sum(int(r.get("socratic_quality", 0)) for r in valid) / n,
        "Helpfulness": sum(int(r.get("helpfulness", 0)) for r in valid) / n,
        "n": n,
    }


def print_comparison_table(metrics_map: Dict[str, Dict]) -> None:
    """Print a simple ASCII comparison table for models."""
    models = list(metrics_map.keys())
    if not models:
        print("No metrics to display.")
        return

    # Header
    print("\n" + "=" * 85)
    header = f"{'METRIC':<30} |"
    for m in models:
        header += f" {m[:15]:<15} |"
    print(header)
    print(f"{'-'*30}-+-{'-'*16}-+-{'-'*16}-")

    rows = [
        ("Code Leakage (Lower is better)", "CLR", "%"),
        ("Direct Answer (Lower is better)", "DAR", "%"),
        ("Fact Correctness (Higher is better)", "FCR", "%"),
        ("Socratic Score (1-5)", "SQ", ""),
        ("Helpfulness (1-5)", "Helpfulness", ""),
    ]

    for label, key, unit in rows:
        row_str = f"{label:<30} |"
        for m in models:
            val = metrics_map.get(m, {}).get(key, 0)
            if isinstance(val, (int, float)):
                row_str += f" {val:8.2f}{unit:<7} |"
            else:
                row_str += f" {str(val):<15} |"
        print(row_str)

    print("=" * 85 + "\n")


# ========================================
# MAIN
# ========================================


def main() -> None:
    if not os.path.exists(RESPONSES_PATH):
        print(f"❌ Error: {RESPONSES_PATH} not found.")
        print("Run generate_test_responses.py first.")
        return

    if not os.path.exists(TEST_CASES_PATH):
        print(f"❌ Error: {TEST_CASES_PATH} not found.")
        print("Run generate_test_cases.py first.")
        return

    with open(TEST_CASES_PATH, "r") as f:
        test_cases = json.load(f)
    with open(RESPONSES_PATH, "r") as f:
        all_responses = json.load(f)

    # Initialize OpenAI Client
    try:
        client = openai.OpenAI()
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")
        print("Check your .env file for OPENAI_API_KEY")
        return

    final_metrics: Dict[str, Dict] = {}
    detailed_logs: Dict[str, List[Dict]] = {}

    print(f"Starting Evaluation using {OPENAI_MODEL}...")

    for model_name, responses in all_responses.items():
        print(f"\n🤖 Evaluating: {model_name}")
        results: List[Dict] = []

        limit = min(len(test_cases), len(responses))

        for i in range(limit):
            print(f"\r  Case {i+1}/{limit}...", end="", flush=True)

            case = test_cases[i]
            buggy_code = case.get("buggy_code", "")
            if not buggy_code and "full_user_message" in case:
                match = re.search(r"```python\s*\n(.*?)\n```", case["full_user_message"], re.DOTALL)
                if match:
                    buggy_code = match.group(1)
                else:
                    buggy_code = "No code found"

            res = evaluate_single_response(client, buggy_code, responses[i])
            results.append(res)

        metrics = calculate_metrics(results)
        final_metrics[model_name] = metrics
        detailed_logs[model_name] = results

        print(f"\n  ✅ Done. SQ: {metrics.get('SQ', 0):.2f}, CLR: {metrics.get('CLR', 0):.1f}%")

    # Save to disk
    with open(RESULTS_PATH, "w") as f:
        json.dump({"metrics": final_metrics, "logs": detailed_logs}, f, indent=2)

    print(f"\n💾 Detailed results saved to: {RESULTS_PATH}")

    # Display Comparison
    if final_metrics:
        print_comparison_table(final_metrics)
    else:
        print("\n❌ No metrics were calculated. Check error logs.")


if __name__ == "__main__":
    main()