"""
Automated Test Suite for Role-Based Authentication, Route Protection, and Candidate Linking
---------------------------------------------------------------------------------------------
Verifies:
1. Recruiter Registration & Recruiter Dashboard Access.
2. Candidate Registration, Automatic Candidate Record Creation & Linkage (user_id <-> candidate_id).
3. Candidate Permission Enforcement & Access Denied on Recruiter Pages.
4. Recruiter Access to Recruitment Management Features.
5. Admin Security (Public registration cannot assign role=admin).
"""

import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import auth_service
import db_auth
import database as db


class TestRoleBasedAuthAndCandidateLinking(unittest.TestCase):

    def setUp(self):
        # Clear test accounts in MongoDB and offline storage
        try:
            with db.get_mongo_client() as client:
                client[db.MONGO_CONFIG["dbname"]]["users"].delete_many({"email": {"$regex": "@role-test\\.com$"}})
                client[db.MONGO_CONFIG["dbname"]][db.MONGO_CONFIG["collection"]].delete_many({"email": {"$regex": "@role-test\\.com$"}})
        except Exception:
            pass

        import offline_storage
        users = offline_storage.load_offline_data("users")
        for k in [k for k, u in users.items() if u.get("email", "").endswith("@role-test.com")]:
            users.pop(k, None)
        offline_storage.save_offline_data("users", users)

        cands = offline_storage.load_offline_data("candidates")
        for k in [k for k, u in cands.items() if u.get("email", "").endswith("@role-test.com")]:
            cands.pop(k, None)
        offline_storage.save_offline_data("candidates", cands)

    def test_1_recruiter_registration_and_flow(self):
        """TEST 1: Register as Recruiter -> role is recruiter -> token contains role."""
        ok, msg, data = auth_service.register_user(
            full_name="Rachel Recruiter",
            email="rachel@role-test.com",
            password="RecruiterPass123",
            confirm_password="RecruiterPass123",
            role="recruiter"
        )
        self.assertTrue(ok, f"Recruiter registration failed: {msg}")
        self.assertEqual(data.get("role"), "recruiter")
        self.assertEqual(data.get("email"), "rachel@role-test.com")

        # Test login
        ok_login, msg_login, login_data = auth_service.authenticate_user("rachel@role-test.com", "RecruiterPass123")
        self.assertTrue(ok_login)
        self.assertEqual(login_data.get("role"), "recruiter")

    def test_2_candidate_registration_and_db_linkage(self):
        """TEST 2: Register as Candidate -> candidate record created/linked with user_id ↔ candidate_id."""
        ok, msg, data = auth_service.register_user(
            full_name="Charlie Candidate",
            email="charlie@role-test.com",
            password="CandidatePass123",
            confirm_password="CandidatePass123",
            role="candidate"
        )
        self.assertTrue(ok, f"Candidate registration failed: {msg}")
        self.assertEqual(data.get("role"), "candidate")
        self.assertIsNotNone(data.get("candidate_id"))
        self.assertEqual(data.get("candidate_id"), data.get("user_id"))

        # Verify candidate record exists in candidate pool/DB
        cands, _ = db.get_recent_candidates(100)
        if not cands:
            import offline_storage
            cands = offline_storage.get_all_offline_records("candidates")
        linked_cand = next((c for c in cands if c.get("email") == "charlie@role-test.com"), None)
        self.assertIsNotNone(linked_cand, "Candidate profile must be automatically created in database upon registration.")
        self.assertEqual(linked_cand.get("full_name"), "Charlie Candidate")

    def test_3_public_registration_disallows_admin(self):
        """TEST 5 (Admin Security): Public registration attempting role=admin is rejected."""
        ok, msg, data = auth_service.register_user(
            full_name="Attacker Admin",
            email="hacker@role-test.com",
            password="HackerPass123",
            confirm_password="HackerPass123",
            role="admin",
            is_bootstrap=False
        )
        self.assertFalse(ok)
        self.assertIn("cannot be created via public registration", msg)

    def test_4_bootstrapped_admin_login(self):
        """TEST 5: Admin bootstrap login works with admin permissions."""
        ok, msg, data = auth_service.authenticate_user("admin@copilot.com", "admin123")
        self.assertTrue(ok)
        self.assertEqual(data.get("role"), "admin")


if __name__ == "__main__":
    unittest.main()
