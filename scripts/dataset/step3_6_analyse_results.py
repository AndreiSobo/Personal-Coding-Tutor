import json
from collections import Counter

def analyze_rejection_patterns():
    with open('../data/validated_examples_COMPLETE.json', 'r') as f:
        all_examples = json.load(f)
    
    rejected = [ex for ex in all_examples 
                if ex['validation']['overall_quality'] == 'reject']
    
    print(f"Analyzing {len(rejected)} rejected examples...\n")
    
    # By error type
    error_types = Counter(ex['error_type'] for ex in rejected)
    print("Rejection by error type:")
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count}")
    
    # By difficulty
    difficulty = Counter(ex['difficulty'] for ex in rejected)
    print("\nRejection by difficulty:")
    for diff, count in difficulty.most_common():
        print(f"  {diff}: {count}")
    
    # Common rejection reasons
    all_issues = []
    for ex in rejected:
        all_issues.extend(ex.get('validation', {}).get('issues', []))
    
    print("\nMost common rejection reasons:")
    for issue, count in Counter(all_issues).most_common(10):
        print(f"  {count}x: {issue[:80]}...")
    
    # Save detailed analysis
    analysis = {
        'total_rejected': len(rejected),
        'by_error_type': dict(error_types),
        'by_difficulty': dict(difficulty),
        'rejection_reasons': dict(Counter(all_issues).most_common(10))
    }
    
    with open('../data/rejection_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print("\n✅ Detailed analysis saved: rejection_analysis.json")

if __name__ == "__main__":
    analyze_rejection_patterns()