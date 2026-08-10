"""
End-to-End Automated Test Suite for Refactored ATS Recruitment Workflow
-----------------------------------------------------------------------
Verifies:
1. Candidate registration & applying for multiple independent jobs.
2. Independent ATS score, recommendation, interview, and decision per application.
3. Recruiter job-centric filtering (candidates filtered by selected job description).
4. ATS Screening eligibility rules (Highly Recommended / Recommended eligible; Needs Improvement disabled).
5. Recruiter Override for ineligible candidates.
6. AI Interview evaluation and recruiter final decision reflecting on candidate dashboard.
"""

import sys
import os
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import db_applications
import db_jobs
import db_interviews
import db_interview_evaluator
import database as db


class TestATSWorkflow(unittest.TestCase):

    def setUp(self):
        db_applications.clear_applications()

        # Create test mock jobs
        self.job1_id = db_jobs.create_job({
            "job_title": "Python Developer",
            "company_name": "Tech Corp",
            "required_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
            "experience_required": "3+ Years",
            "location": "Remote",
            "salary": "$120,000",
            "job_description": "Building scalable Python backends with FastAPI and Docker."
        })

        self.job2_id = db_jobs.create_job({
            "job_title": "DevOps Engineer",
            "company_name": "CloudOps Solutions",
            "required_skills": ["Kubernetes", "AWS", "Terraform", "CI/CD"],
            "experience_required": "4+ Years",
            "location": "Hybrid",
            "salary": "$130,000",
            "job_description": "Managing AWS infrastructure, Terraform, Kubernetes, and CI/CD pipelines."
        })

        # Test Candidate 1: Rahul (Python & DevOps skills)
        self.rahul = {
            "candidate_id": "CAND-RAHUL",
            "full_name": "Rahul Sharma",
            "email": "rahul@example.com",
            "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes", "AWS"],
            "experience": "5 years experience in Python backend engineering.",
            "education": "B.Tech Computer Science",
            "raw_text": "Experienced Python Backend Developer with FastAPI, Docker, and Kubernetes skills."
        }

        # Test Candidate 2: Priya (Python skills only)
        self.priya = {
            "candidate_id": "CAND-PRIYA",
            "full_name": "Priya Patel",
            "email": "priya@example.com",
            "skills": ["Python", "Django", "FastAPI"],
            "experience": "4 years experience in Python Django development.",
            "education": "M.Tech Software Engineering",
            "raw_text": "Python Developer proficient in Django and REST APIs."
        }

        # Test Candidate 3: Vikas (DevOps skills only)
        self.vikas = {
            "candidate_id": "CAND-VIKAS",
            "full_name": "Vikas Verma",
            "email": "vikas@example.com",
            "skills": ["Kubernetes", "AWS", "Terraform", "Docker"],
            "experience": "5 years experience in Terraform, AWS, and Kubernetes.",
            "education": "B.Sc Information Technology",
            "raw_text": "DevOps Engineer with 5 years experience in Terraform, AWS, and Kubernetes."
        }

        # Test Candidate 4: Ineligible Candidate (Low match skills)
        self.ineligible_cand = {
            "candidate_id": "CAND-LOWMATCH",
            "full_name": "Aman Lowmatch",
            "email": "aman@example.com",
            "skills": ["HTML", "CSS"],
            "experience": "1 year junior experience.",
            "education": "Diploma Graphic Design",
            "raw_text": "Junior frontend designer with basic HTML CSS skills."
        }

    def test_job_specific_independent_applications(self):
        """Verify candidate can apply to multiple jobs and each application is independent."""
        job1 = db_jobs.get_job_by_id(self.job1_id)
        job2 = db_jobs.get_job_by_id(self.job2_id)

        # Rahul applies for Python Developer
        ok1, msg1, app1 = db_applications.evaluate_and_apply(self.rahul, job1)
        self.assertTrue(ok1, f"Failed to apply for Python Developer: {msg1}")
        self.assertIsNotNone(app1)

        # Rahul applies for DevOps Engineer
        ok2, msg2, app2 = db_applications.evaluate_and_apply(self.rahul, job2)
        self.assertTrue(ok2, f"Failed to apply for DevOps Engineer: {msg2}")
        self.assertIsNotNone(app2)

        # Confirm Rahul has 2 independent applications
        rahul_apps = db_applications.get_applications_by_candidate("CAND-RAHUL", "rahul@example.com")
        self.assertEqual(len(rahul_apps), 2)
        self.assertNotEqual(app1["application_id"], app2["application_id"])
        self.assertNotEqual(app1["job_id"], app2["job_id"])

    def test_recruiter_job_centric_filtering(self):
        """Verify recruiter sees ONLY candidates who applied for the specific job description."""
        job1 = db_jobs.get_job_by_id(self.job1_id)
        job2 = db_jobs.get_job_by_id(self.job2_id)

        # Rahul & Priya apply for Python Developer
        db_applications.evaluate_and_apply(self.rahul, job1)
        db_applications.evaluate_and_apply(self.priya, job1)

        # Vikas applies for DevOps Engineer
        db_applications.evaluate_and_apply(self.vikas, job2)

        # Recruiter checks Python Developer job
        python_apps = db_applications.get_applications_by_job(self.job1_id)
        python_cand_ids = {a["candidate_id"] for a in python_apps}
        self.assertIn("CAND-RAHUL", python_cand_ids)
        self.assertIn("CAND-PRIYA", python_cand_ids)
        self.assertNotIn("CAND-VIKAS", python_cand_ids)

        # Recruiter checks DevOps Engineer job
        devops_apps = db_applications.get_applications_by_job(self.job2_id)
        devops_cand_ids = {a["candidate_id"] for a in devops_apps}
        self.assertIn("CAND-VIKAS", devops_cand_ids)
        self.assertNotIn("CAND-PRIYA", devops_cand_ids)

    def test_ats_screening_recommendation_and_override(self):
        """Verify ATS eligibility screening rules and recruiter override."""
        job1 = db_jobs.get_job_by_id(self.job1_id)

        # Rahul has strong match -> Highly Recommended / Recommended -> Eligible
        ok_r, _, app_r = db_applications.evaluate_and_apply(self.rahul, job1)
        is_r_eligible = db_applications.is_eligible_for_interview(app_r["recommendation"], app_r.get("is_overridden", False))
        self.assertTrue(is_r_eligible, "Highly matching candidate should be eligible.")

        # Ineligible candidate has low match -> Needs Improvement / Not Recommended -> Ineligible
        ok_i, _, app_i = db_applications.evaluate_and_apply(self.ineligible_cand, job1)
        is_i_eligible_before = db_applications.is_eligible_for_interview(app_i["recommendation"], app_i.get("is_overridden", False))
        self.assertFalse(is_i_eligible_before, "Low matching candidate should NOT be eligible by default.")

        # Apply Recruiter Override for ineligible candidate
        ok_ov, msg_ov = db_applications.override_application_eligibility(app_i["application_id"], "Verified candidate portfolio.")
        self.assertTrue(ok_ov, "Recruiter override should succeed.")

        updated_app_i = db_applications.get_application_by_id(app_i["application_id"])
        self.assertTrue(updated_app_i["is_overridden"])
        is_i_eligible_after = db_applications.is_eligible_for_interview(updated_app_i["recommendation"], updated_app_i["is_overridden"])
        self.assertTrue(is_i_eligible_after, "Candidate should become eligible after Recruiter Override.")

    def test_interview_assignment_evaluation_and_final_decision(self):
        """Verify full end-to-end interview assignment, evaluation, and recruiter final decision updates."""
        job1 = db_jobs.get_job_by_id(self.job1_id)
        db_applications.evaluate_and_apply(self.rahul, job1)

        # Recruiter assigns interview
        questions = ["Explain FastAPI dependency injection.", "How do you optimize Docker containers?"]
        ok_intv, msg_intv, iid = db_interviews.create_interview_assignment(
            candidate_id="CAND-RAHUL",
            job_id=self.job1_id,
            questions=questions,
            due_date="2026-08-15"
        )
        self.assertTrue(ok_intv, f"Assign interview failed: {msg_intv}")

        # Check application status updated to Interview Assigned
        app_after_assign = db_applications.get_application("CAND-RAHUL", self.job1_id)
        self.assertEqual(app_after_assign["interview_status"], "Assigned")

        # Candidate submits answers
        responses = [
            {"question": questions[0], "answer": "FastAPI uses Depends() for dependency injection."},
            {"question": questions[1], "answer": "Multi-stage builds and minimal base images like alpine."}
        ]
        ok_sub, msg_sub = db_interviews.submit_interview_responses(
            interview_id=iid,
            candidate_id="CAND-RAHUL",
            job_id=self.job1_id,
            responses_list=responses
        )
        self.assertTrue(ok_sub, f"Submit interview failed: {msg_sub}")

        # Save AI Evaluation
        evals = [
            {"question": questions[0], "answer": responses[0]["answer"], "technical_score": 90, "communication_score": 85, "confidence_score": 90, "overall_score": 88, "feedback": "Good understanding"},
            {"question": questions[1], "answer": responses[1]["answer"], "technical_score": 92, "communication_score": 90, "confidence_score": 90, "overall_score": 91, "feedback": "Excellent response"}
        ]
        summary = {
            "overall_interview_score": 90,
            "avg_technical_score": 91,
            "avg_communication_score": 88,
            "avg_confidence_score": 90,
            "final_recommendation": "Highly Recommended"
        }

        ok_eval, msg_eval = db_interview_evaluator.save_interview_evaluations(iid, "CAND-RAHUL", self.job1_id, evals, summary)
        self.assertTrue(ok_eval, f"Save evaluation failed: {msg_eval}")

        # Verify application status & interview score updated
        app_after_eval = db_applications.get_application("CAND-RAHUL", self.job1_id)
        self.assertEqual(app_after_eval["interview_status"], "Evaluated")
        self.assertEqual(app_after_eval["interview_score"], 90)

        # Recruiter makes Final Decision: Selected
        ok_dec, msg_dec = db_applications.set_application_final_decision("CAND-RAHUL", self.job1_id, "Selected")
        self.assertTrue(ok_dec, f"Set final decision failed: {msg_dec}")

        # Candidate Dashboard view check
        app_final = db_applications.get_application("CAND-RAHUL", self.job1_id)
        self.assertEqual(app_final["final_decision"], "Selected")
        self.assertEqual(app_final["status"], "Selected (Hired)")

    def test_ats_dashboard_metrics_and_filters(self):
        """Verify ATS Dashboard metric calculations, card counts, and job filters."""
        job1 = db_jobs.get_job_by_id(self.job1_id)
        job2 = db_jobs.get_job_by_id(self.job2_id)

        # Apply candidates to jobs
        db_applications.evaluate_and_apply(self.rahul, job1)
        db_applications.evaluate_and_apply(self.priya, job1)
        db_applications.evaluate_and_apply(self.vikas, job2)
        db_applications.evaluate_and_apply(self.ineligible_cand, job1)

        all_apps = db_applications.get_all_applications()
        self.assertEqual(len(all_apps), 4, "Total applications should be 4 across all jobs.")

        # Test card counts for Recommended & Highly Recommended
        rec_apps = [a for a in all_apps if a.get("recommendation") in ["Recommended", "Highly Recommended", "Excellent Match"]]
        self.assertTrue(len(rec_apps) >= 2, "Should have at least 2 recommended candidates.")

        # Test job position filtering for DevOps Engineer (job2)
        devops_apps = [a for a in all_apps if a.get("job_id") == self.job2_id]
        self.assertEqual(len(devops_apps), 1)
        self.assertEqual(devops_apps[0]["candidate_id"], "CAND-VIKAS")


if __name__ == "__main__":
    unittest.main()
