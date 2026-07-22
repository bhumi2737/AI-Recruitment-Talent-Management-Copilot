"""
Backfill Evaluations Script
---------------------------
Evaluates all candidates stored in MongoDB against all active job descriptions
and saves/upserts the evaluation documents into the evaluations collection.
"""

import sys
import os

# Ensure local directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
import db_jobs
from jd_matcher import calculate_candidate_score

def main():
    print("Testing MongoDB connection...")
    ok, msg = db.test_connection()
    if not ok:
        print(f"Error: {msg}")
        return

    print("Fetching candidates and job descriptions...")
    candidates = db.get_all_candidates(include_raw_text=True)
    jobs = db_jobs.get_all_jobs()

    print(f"Found {len(candidates)} candidate(s) and {len(jobs)} job posting(s).")
    if not candidates or not jobs:
        print("Nothing to evaluate.")
        return

    eval_count = 0
    for cand in candidates:
        cand_id = str(cand.get("id") or cand.get("_id") or cand.get("email"))
        cand_name = cand.get("full_name", "Unknown Candidate")
        print(f"\nEvaluating Candidate: {cand_name} (ID: {cand_id})")

        for job in jobs:
            job_id = str(job.get("job_id", ""))
            job_title = job.get("job_title", "Unknown Role")

            ats_res = calculate_candidate_score(cand, job)
            hiring_score = ats_res.get("hiring_score", 0)
            recommendation = ats_res.get("recommendation", "Not Recommended")
            breakdown = ats_res.get("score_breakdown", {})

            success, err_msg = db.save_evaluation(
                job_id=job_id,
                candidate_id=cand_id,
                hiring_score=hiring_score,
                recommendation=recommendation,
                score_breakdown=breakdown
            )
            if success:
                print(f"  -> Match with '{job_title}': Score {hiring_score}% ({recommendation}) [Saved]")
                eval_count += 1
            else:
                print(f"  -> Failed to save evaluation for '{job_title}': {err_msg}")

    print(f"\nSuccess! Backfilled {eval_count} evaluation document(s) into MongoDB.")

if __name__ == "__main__":
    main()
