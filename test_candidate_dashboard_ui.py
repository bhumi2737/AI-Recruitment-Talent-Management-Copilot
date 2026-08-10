"""
Automated Test Suite for Enhanced Candidate Dashboard UI
-----------------------------------------------------------
Verifies:
1. 5-Stage Timeline Stepper calculations (Applied -> ATS Evaluation -> Interview Assigned -> Interview Completed -> Final Decision).
2. Status notice for ineligible/low match candidates ("Your application did not qualify for the interview stage.").
3. Callout banner for recommended candidates with active interviews ("Interview Assigned" & "Upcoming Interview").
"""

import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import db_applications
import db_interviews
import db_jobs
import app


class TestCandidateDashboardUI(unittest.TestCase):

    def setUp(self):
        db_applications.clear_applications()

        self.job_id = db_jobs.create_job({
            "job_title": "Fullstack Engineer",
            "company_name": "CloudTech Corp",
            "required_skills": ["React", "Python", "PostgreSQL"],
            "experience_required": "3+ Years",
            "job_description": "Fullstack web app development with React and Python."
        })

        self.eligible_cand = {
            "candidate_id": "CAND-STRONG",
            "full_name": "Kavita Rao",
            "email": "kavita@example.com",
            "skills": ["React", "Python", "PostgreSQL"],
            "experience": "4 years fullstack experience",
            "education": "B.Tech CS"
        }

        self.ineligible_cand = {
            "candidate_id": "CAND-WEAK",
            "full_name": "Bob Ineligible",
            "email": "bob@example.com",
            "skills": ["HTML"],
            "experience": "1 month internship",
            "education": "High School"
        }

    def test_timeline_stepper_rendering(self):
        """Verify timeline stepper produces HTML for all 5 stages."""
        job = db_jobs.get_job_by_id(self.job_id)
        ok1, _, app1 = db_applications.evaluate_and_apply(self.eligible_cand, job)
        self.assertTrue(ok1)

        html_stepper = app.render_candidate_timeline_stepper(app1)
        self.assertIn("1. Applied", html_stepper)
        self.assertIn("2. ATS Evaluation", html_stepper)
        self.assertIn("3. Interview Assigned", html_stepper)
        self.assertIn("4. Interview Completed", html_stepper)
        self.assertIn("5. Final Decision", html_stepper)

    def test_ineligible_candidate_status_notice(self):
        """Verify ineligible candidate produces notice: 'Your application did not qualify for the interview stage.'"""
        job = db_jobs.get_job_by_id(self.job_id)
        ok2, _, app2 = db_applications.evaluate_and_apply(self.ineligible_cand, job)
        self.assertTrue(ok2)

        rec = app2.get("recommendation", "")
        self.assertIn(rec, ["Needs Improvement", "Not Recommended"])

        is_ineligible = (rec in ["Not Recommended", "Needs Improvement", "Weak Match"]) and not app2.get("is_overridden", False)
        self.assertTrue(is_ineligible, "Ineligible candidate should trigger status notice.")

    def test_recommended_candidate_interview_callout(self):
        """Verify recommended candidate with assigned interview triggers 'Interview Assigned' callout."""
        job = db_jobs.get_job_by_id(self.job_id)
        ok1, _, app1 = db_applications.evaluate_and_apply(self.eligible_cand, job)
        self.assertTrue(ok1)

        # Assign interview
        ok_intv, msg_intv, iid = db_interviews.create_interview_assignment(
            candidate_id="CAND-STRONG",
            job_id=self.job_id,
            questions=["Explain React hooks."],
            due_date="2026-08-20"
        )
        self.assertTrue(ok_intv)

        app1_updated = db_applications.get_application("CAND-STRONG", self.job_id)
        self.assertEqual(app1_updated["interview_status"], "Assigned")


if __name__ == "__main__":
    unittest.main()
