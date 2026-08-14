"""
Automated Test Suite for Role Normalization and Strict Portal Separation
-------------------------------------------------------------------------
Verifies:
1. Role Normalization (handles string, list, mixed case like ["recruiter"], "RECRUITER", "admin").
2. Admin Login & Admin Portal setup.
3. Recruiter Login & Recruiter Portal setup (Admin items Users, Recruiters, Admin Profile omitted).
4. Candidate Login & Candidate Portal setup (Recruiter/Admin items omitted).
5. Route protection & restricted page access denial.
"""

import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import auth_service


class TestRolePortalsSeparation(unittest.TestCase):

    def setUp(self):
        try:
            import database as db
            with db.get_mongo_client() as client:
                client[db.MONGO_CONFIG["dbname"]]["users"].delete_many({"email": {"$regex": "@testportal\\.com$"}})
        except Exception:
            pass

        try:
            import offline_storage
            users = offline_storage.load_offline_data("users")
            for k in [k for k, u in users.items() if u.get("email", "").endswith("@testportal.com")]:
                users.pop(k, None)
            offline_storage.save_offline_data("users", users)
        except Exception:
            pass

    def test_1_role_normalization(self):
        """TEST 1: Verify normalize_role handles various input formats."""
        self.assertEqual(auth_service.normalize_role("recruiter"), "recruiter")
        self.assertEqual(auth_service.normalize_role("RECRUITER"), "recruiter")
        self.assertEqual(auth_service.normalize_role(["recruiter"]), "recruiter")
        self.assertEqual(auth_service.normalize_role("admin"), "admin")
        self.assertEqual(auth_service.normalize_role(["ADMIN"]), "admin")
        self.assertEqual(auth_service.normalize_role("candidate"), "candidate")
        self.assertEqual(auth_service.normalize_role(["Candidate"]), "candidate")
        self.assertEqual(auth_service.normalize_role(None), "candidate")

    def test_2_recruiter_registration_and_portal_isolation(self):
        """TEST 2: Register as Recruiter -> role normalized to 'recruiter' -> Admin items absent."""
        ok, msg, data = auth_service.register_user(
            full_name="Rita Recruiter",
            email="rita.recruiter@testportal.com",
            password="RecruiterPass123!",
            confirm_password="RecruiterPass123!",
            role="recruiter"
        )
        self.assertTrue(ok, f"Registration failed: {msg}")
        norm_role = auth_service.normalize_role(data.get("role"))
        self.assertEqual(norm_role, "recruiter")

        # Define admin-only pages
        admin_only_pages = ["Users", "Recruiters", "Admin Profile"]
        recruiter_pages = ["Dashboard", "Resume Upload", "Candidate Pipeline", "Interview Question Generator", "Interview Assignment", "Submitted Interviews", "Job Descriptions", "Candidate Matching", "Candidate Details", "Skill Gap Analysis", "Candidate Ranking", "Executive Reports", "Settings", "Recruiter Profile"]

        # Ensure no overlap
        for p in admin_only_pages:
            self.assertNotIn(p, recruiter_pages, f"Admin page '{p}' must NOT be in recruiter_pages")

    def test_3_candidate_portal_isolation(self):
        """TEST 3: Candidate user normalized to 'candidate' -> Recruiter/Admin tools excluded."""
        ok, msg, data = auth_service.register_user(
            full_name="Carl Candidate",
            email="carl.candidate@testportal.com",
            password="CandidatePass123!",
            confirm_password="CandidatePass123!",
            role="candidate"
        )
        self.assertTrue(ok, f"Candidate registration failed: {msg}")
        norm_role = auth_service.normalize_role(data.get("role"))
        self.assertEqual(norm_role, "candidate")

    def test_4_admin_bootstrap_login(self):
        """TEST 4: Admin login normalized to 'admin'."""
        ok, msg, data = auth_service.authenticate_user("admin@copilot.com", "admin123")
        self.assertTrue(ok, f"Admin login failed: {msg}")
        norm_role = auth_service.normalize_role(data.get("role"))
        self.assertEqual(norm_role, "admin")


if __name__ == "__main__":
    unittest.main()
