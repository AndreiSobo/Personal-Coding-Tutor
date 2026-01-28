import json
from collections import Counter

def analyze_rejections():
    with open('../data/validated_examples.json', 'r') as f:
        all_examples = json.load(f)
    
    # Count by problem
    problem_stats = Counter()
    problem_titles = {}
    
    for ex in all_examples:
        problem_id = ex['problem_id']
        problem_titles[problem_id] = ex['problem_title']
        
        if ex['validation']['overall_quality'] == 'reject':
            problem_stats[problem_id] += 1
    
    # Find problems with 2+ rejections
    retry_problems = []
    
    print("Problems with 2-3 rejections (candidates for regeneration):")
    print("-" * 60)
    
    for prob_id, count in problem_stats.most_common():
        if count >= 2:
            print(f"  ID {prob_id}: {problem_titles[prob_id]} ({count}/3 rejected)")
            retry_problems.append({
                'id': prob_id,
                'title': problem_titles[prob_id],
                'rejections': count
            })
    
    # Save to file for step2 to use
    output_path = '../data/retry_problem_ids.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(retry_problems, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Total: {len(retry_problems)} problems to regenerate")
    print(f"Saved to: {output_path}")
    print(f"{'='*60}")
    
    return retry_problems

if __name__ == "__main__":
    analyze_rejections()