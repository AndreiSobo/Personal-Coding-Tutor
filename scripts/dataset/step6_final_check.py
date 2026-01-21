"""
Step 6: Final Quality Check
============================
This script runs automated checks on the formatted dataset
to catch any remaining issues before training.

Input: data/training_data.jsonl
Output: Console report (pass/fail)
"""

import json
import re
import os
from typing import List, Tuple
from collections import Counter


def check_structure(example: dict, index: int) -> List[str]:
    """Check the basic structure of an example."""
    issues = []
    
    messages = example.get('messages', [])
    
    # Check message count
    if len(messages) != 3:
        issues.append(f"Example {index}: Expected 3 messages, got {len(messages)}")
        return issues  # Can't check further
    
    # Check roles
    expected_roles = ['system', 'user', 'assistant']
    for i, (msg, expected_role) in enumerate(zip(messages, expected_roles)):
        if msg.get('role') != expected_role:
            issues.append(f"Example {index}: Message {i} should be '{expected_role}', got '{msg.get('role')}'")
    
    # Check content exists
    for i, msg in enumerate(messages):
        if not msg.get('content'):
            issues.append(f"Example {index}: Message {i} has empty content")
    
    return issues


def check_hint_quality(hint: str, index: int) -> List[str]:
    """Check the quality of the Socratic hint."""
    issues = []
    
    # Check for code blocks
    if '```' in hint:
        issues.append(f"Example {index}: Hint contains code block (```)")
    
    # Check for inline code
    if re.search(r'`[^`]+`', hint):
        issues.append(f"Example {index}: Hint contains inline code (`...`)")
    
    # Check for function definitions
    if re.search(r'\bdef\s+\w+\s*\(', hint):
        issues.append(f"Example {index}: Hint contains function definition")
    
    # Check for common code patterns
    code_patterns = [
        (r'\bfor\s+\w+\s+in\s+', "for loop"),
        (r'\bwhile\s+.+:', "while loop"),
        (r'\bif\s+.+:', "if statement"),
        (r'\breturn\s+\[', "return statement"),
        (r'\w+\s*=\s*\[\]', "list initialization"),
        (r'\w+\s*=\s*\{\}', "dict initialization"),
        (r'\w+\s*=\s*\d+', "variable assignment"),
    ]
    
    for pattern, name in code_patterns:
        if re.search(pattern, hint):
            issues.append(f"Example {index}: Hint may contain {name}")
    
    # Check for direct answer patterns
    direct_patterns = [
        (r'\bchange\s+.+\s+to\s+', "directive: 'change X to Y'"),
        (r'\breplace\s+.+\s+with\s+', "directive: 'replace X with Y'"),
        (r'\byou\s+(?:need|should|must)\s+(?:to\s+)?(?:use|change|add|remove)', "directive language"),
        (r'\bthe\s+(?:answer|solution|fix)\s+is\b', "reveals answer"),
        (r'\bjust\s+(?:add|change|use|remove)\b', "directive: 'just do X'"),
    ]
    
    hint_lower = hint.lower()
    for pattern, description in direct_patterns:
        if re.search(pattern, hint_lower):
            issues.append(f"Example {index}: Hint contains {description}")
    
    # Check hint length
    if len(hint) < 50:
        issues.append(f"Example {index}: Hint too short ({len(hint)} chars)")
    if len(hint) > 1000:
        issues.append(f"Example {index}: Hint too long ({len(hint)} chars)")
    
    # Check for question (good sign for Socratic hints)
    # This is informational, not an issue
    
    return issues


def check_user_message(user_content: str, index: int) -> List[str]:
    """Check the user message format."""
    issues = []
    
    # Should contain problem title
    if 'Problem:' not in user_content:
        issues.append(f"Example {index}: User message missing 'Problem:' header")
    
    # Should contain code block
    if '```python' not in user_content:
        issues.append(f"Example {index}: User message missing Python code block")
    
    # Should not be too short
    if len(user_content) < 100:
        issues.append(f"Example {index}: User message too short ({len(user_content)} chars)")
    
    return issues


def run_all_checks(filepath: str) -> Tuple[bool, List[str]]:
    """Run all quality checks on the dataset."""
    
    all_issues = []
    
    # Load dataset
    examples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                example = json.loads(line.strip())
                examples.append(example)
            except json.JSONDecodeError as e:
                all_issues.append(f"Line {line_num}: Invalid JSON - {e}")
    
    if not examples:
        return False, ["No valid examples found in dataset"]
    
    # Run checks on each example
    for i, example in enumerate(examples):
        # Structure check
        all_issues.extend(check_structure(example, i))
        
        # Skip content checks if structure is broken
        messages = example.get('messages', [])
        if len(messages) != 3:
            continue
        
        # User message check
        user_content = messages[1].get('content', '')
        all_issues.extend(check_user_message(user_content, i))
        
        # Hint quality check
        hint = messages[2].get('content', '')
        all_issues.extend(check_hint_quality(hint, i))
    
    return len(all_issues) == 0, all_issues


def main():
    filepath = '../data/training_data.jsonl'
    
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found. Run step5_format_for_training.py first.")
        return
    
    print("Running quality checks on training dataset...")
    print("-" * 50)
    
    passed, issues = run_all_checks(filepath)
    
    # Count examples
    with open(filepath, 'r') as f:
        num_examples = sum(1 for _ in f)
    
    print("\n" + "=" * 50)
    print("QUALITY CHECK RESULTS")
    print("=" * 50)
    print(f"Total examples: {num_examples}")
    print(f"Issues found: {len(issues)}")
    
    if passed:
        print("\n✅ ALL CHECKS PASSED!")
        print("\nYour dataset is ready for training.")
    else:
        print(f"\n⚠️  ISSUES DETECTED ({len(issues)})")
        
        # Group issues by type
        issue_types = Counter()
        for issue in issues:
            # Extract issue type (after the colon)
            if ':' in issue:
                issue_type = issue.split(':', 2)[-1].strip()
                issue_types[issue_type] += 1
        
        print("\nIssue summary:")
        for issue_type, count in issue_types.most_common(10):
            print(f"  - {issue_type}: {count}")
        
        print("\nFirst 20 specific issues:")
        for issue in issues[:20]:
            print(f"  • {issue}")
        
        if len(issues) > 20:
            print(f"\n  ... and {len(issues) - 20} more issues")
        
        print("\n" + "-" * 50)
        print("RECOMMENDATION:")
        print("Review and fix the issues above before training.")
        print("You may need to re-run step4 (revision) or manually edit examples.")
    
    # Additional stats
    print("\n" + "-" * 50)
    print("DATASET STATISTICS")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        hints = []
        has_question = 0
        for line in f:
            example = json.loads(line)
            hint = example['messages'][2]['content']
            hints.append(hint)
            if '?' in hint:
                has_question += 1
    
    avg_hint_length = sum(len(h) for h in hints) / len(hints)
    
    print(f"Average hint length: {avg_hint_length:.0f} characters")
    print(f"Hints containing questions: {has_question}/{len(hints)} ({100*has_question/len(hints):.1f}%)")
    
    # Hint length distribution
    short = sum(1 for h in hints if len(h) < 100)
    medium = sum(1 for h in hints if 100 <= len(h) < 300)
    long = sum(1 for h in hints if len(h) >= 300)
    
    print(f"Hint length distribution:")
    print(f"  - Short (<100 chars):  {short} ({100*short/len(hints):.1f}%)")
    print(f"  - Medium (100-300):    {medium} ({100*medium/len(hints):.1f}%)")
    print(f"  - Long (300+):         {long} ({100*long/len(hints):.1f}%)")


if __name__ == "__main__":
    main()
