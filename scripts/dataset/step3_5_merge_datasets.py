"""
Merge original and retry validated examples - COMPLETE DATASET
Output: Full historical record for research transparency
"""
import json

def merge_all_validated_examples():
    # Load original validated examples (288 examples)
    with open('../data/validated_examples.json', 'r') as f:
        original = json.load(f)
    
    print(f"Original validated examples: {len(original)}")
    
    # Load ALL retry validated examples
    retry_files = [
        '../data/examples_passed_RETRY.json',
        '../data/examples_rejected_RETRY.json',
        '../data/examples_needs_revision_RETRY.json'
    ]
    
    retry_examples = []
    for file_path in retry_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                retry_examples.extend(data)
                print(f"  Loaded {len(data)} from {file_path.split('/')[-1]}")
        except FileNotFoundError:
            print(f"  ⚠️  {file_path} not found")
    
    print(f"\nRetry validated examples: {len(retry_examples)}")
    
    # Get problem IDs that were regenerated
    retry_problem_ids = {ex['problem_id'] for ex in retry_examples}
    print(f"Problems regenerated: {len(retry_problem_ids)}")
    
    # Remove old versions of retry problems from original
    original_filtered = [ex for ex in original 
                        if ex['problem_id'] not in retry_problem_ids]
    
    print(f"Original after removing regenerated problems: {len(original_filtered)}")
    
    # Combine ALL examples
    final_all = original_filtered + retry_examples
    
    # Statistics for research reporting
    passed = [ex for ex in final_all if ex['validation']['overall_quality'] == 'pass']
    rejected = [ex for ex in final_all if ex['validation']['overall_quality'] == 'reject']
    needs_revision = [ex for ex in final_all if ex['validation']['overall_quality'] == 'needs_revision']
    
    print(f"\n{'='*60}")
    print(f"COMPLETE VALIDATED DATASET")
    print(f"{'='*60}")
    print(f"Total examples: {len(final_all)}")
    print(f"  ✓ Passed:         {len(passed):3d} ({100*len(passed)/len(final_all):.1f}%)")
    print(f"  ✗ Rejected:       {len(rejected):3d} ({100*len(rejected)/len(final_all):.1f}%)")
    print(f"  ⚠ Needs revision: {len(needs_revision):3d} ({100*len(needs_revision)/len(final_all):.1f}%)")
    
    # Save complete dataset (for research records)
    with open('../data/validated_examples_COMPLETE.json', 'w') as f:
        json.dump(final_all, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Complete dataset saved: validated_examples_COMPLETE.json")
    
    # Also save just passed examples (for training)
    with open('../data/training_dataset_final.json', 'w') as f:
        json.dump(passed, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Training dataset saved: training_dataset_final.json ({len(passed)} examples)")
    
    return {
        'total': len(final_all),
        'passed': len(passed),
        'rejected': len(rejected),
        'needs_revision': len(needs_revision)
    }

if __name__ == "__main__":
    stats = merge_all_validated_examples()