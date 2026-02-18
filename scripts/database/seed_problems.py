"""
Seed the problems from huggingface newfacade/LeetCodeDataset into the Supabase content_problems database
Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY exported to environment
"""

import os
import json
import sys
from datasets import load_dataset
from supabase import create_client, Client


# config

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
DATASET_NAME = "newfacade/LeetCodeDataset"
DATASET_SPLIT = "train"
BATCH_SIZE = 100


# utils

def transform_row(row: dict) -> dict:
    """
    Map a HuggingFace dataset row to the content_problems schema.

    Dataset fields   →  DB columns
    ─────────────────────────────────────────
    task_id          →  slug
    task_id (derive) →  title
    question_id      →  question_id
    difficulty       →  difficulty
    tags             →  tags (jsonb)
    problem_description → description
    starter_code     →  starter_code
    completion       →  solution_code
    entry_point      →  entry_point
    input_output     →  input_output (jsonb)
    test             →  test_code
    """
    # input_output: list of dicts with input/output keys
    io_pairs = row.get("input_output", [])
    if isinstance(io_pairs, list):
        io_pairs = json.loads(json.dumps(io_pairs, default=str))

    # tags: list of strings like ["Array", "Hash Table"]
    tags = row.get("tags", [])
    if isinstance(tags, list):
        tags = json.loads(json.dumps(tags))

    return {
        "slug": row["task_id"],
        "question_id": row.get("question_id"),
        "difficulty": row.get("difficulty"),
        "tags": tags,
        "description": row.get("problem_description", ""),
        "starter_code": row.get("starter_code", ""),
        "solution_code": row.get("completion", ""),
        "entry_point": row.get("entry_point", ""),
        "input_output": io_pairs,
        "test_code": row.get("test", ""),
    }


def batch_upsert(supabase: Client, rows: list[dict]) -> int:
    """Upsert a batch into content_problems. Uses slug as conflict target."""
    response = (
        supabase.table("content_problems")
        .upsert(rows, on_conflict="slug")
        .execute()
    )
    return len(response.data) if response.data else 0


def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("Error with SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY variables")
        sys.exit(1)

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    print(f"Loading dataset '{DATASET_NAME}' (split: {DATASET_SPLIT})...")
    dataset = load_dataset(DATASET_NAME, split=DATASET_SPLIT)
    total = len(dataset)
    print(f"Loaded {total} problems.\n")

    batch = []
    inserted = 0
    skipped = 0

    for i, row in enumerate(dataset):
        try:
            transformed = transform_row(row)
            batch.append(transformed)
        except Exception as e:
            print(f"  WARN: Skipping row {i} ({row.get('task_id', '?')}): {e}")
            skipped += 1
            continue

        if len(batch) >= BATCH_SIZE:
            count = batch_upsert(supabase, batch)
            inserted += count
            print(f"  Progress: {inserted}/{total} ({(inserted/total)*100:.1f}%)")
            batch = []

    # Flush remaining
    if batch:
        count = batch_upsert(supabase, batch)
        inserted += count

    print(f"Done! Inserted {inserted} problems, skipped {skipped}.")

    # Verification
    response = supabase.table("content_problems").select("id", count="exact").execute()
    print(f"Total problems in database: {response.count}")

    for diff in ["Easy", "Medium", "Hard"]:
        resp = (
            supabase.table("content_problems")
            .select("id", count="exact")
            .eq("difficulty", diff)
            .execute()
        )
        print(f"  {diff}: {resp.count}")


if __name__ == "__main__":
    main()