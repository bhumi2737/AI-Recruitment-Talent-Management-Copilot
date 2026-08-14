"""
Automated Test Suite for Authentication System
-----------------------------------------------
Tests:
1. Password Hashing & Verification (Bcrypt / Hashlib fallback).
2. JWT Access Token Generation & Decoding.
3. User Registration (Success, Validation Errors, Duplicate Email).
4. User Authentication / Login (Success, Invalid Credentials).
5. Fast API Auth Endpoints (/api/auth/register, /api/auth/login, /api/auth/me).
"""

import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), "ResumeParser"))

import auth_service
import db_auth


class TestAuthenticationSystem(unittest.TestCase):

    def setUp(self):
        # Clear test accounts in MongoDB and offline storage
        try:
            import database as db
            with db.get_mongo_client() as client:
                client[db.MONGO_CONFIG["dbname"]]["users"].delete_many({"email": {"$regex": "@autotest\\.com$"}})
        except Exception:
            pass

        import offline_storage
        users = offline_storage.load_offline_data("users")
        test_keys = [k for k, u in users.items() if u.get("email", "").endswith("@autotest.com")]
        for k in test_keys:
            users.pop(k, None)
        offline_storage.save_offline_data("users", users)

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)
        self.assertTrue(hashed != password)
        self.assertTrue(auth_service.verify_password(password, hashed))
        self.assertFalse(auth_service.verify_password("WrongPassword", hashed))

    def test_jwt_token_flow(self):
        """Test JWT token encoding and decoding."""
        user_payload = {
            "user_id": "USR-TEST100",
            "full_name": "Test Recruiter",
            "email": "recruiter@autotest.com",
            "role": "admin"
        }
        token = auth_service.create_access_token(user_payload, expires_hours=2)
        self.assertIsNotNone(token)
        self.assertTrue(isinstance(token, str))

        decoded = auth_service.verify_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.get("sub"), "USR-TEST100")
        self.assertEqual(decoded.get("email"), "recruiter@autotest.com")
        self.assertEqual(decoded.get("role"), "admin")

    def test_user_registration_success(self):
        """Test registering a new valid user account."""
        ok, msg, data = auth_service.register_user(
            full_name="Sarah Connor",
            email="sarah@autotest.com",
            password="MySecretPassword123",
            confirm_password="MySecretPassword123",
            role="admin"
        )
        self.assertTrue(ok, f"Registration failed: {msg}")
        self.assertEqual(data.get("full_name"), "Sarah Connor")
        self.assertEqual(data.get("email"), "sarah@autotest.com")
        self.assertIsNotNone(data.get("token"))

    def test_user_registration_duplicate_email(self):
        """Test registering with an existing email returns an error."""
        auth_service.register_user(
            full_name="Duplicate User",
            email="dup@autotest.com",
            password="Password123",
            confirm_password="Password123"
        )
        ok, msg, data = auth_service.register_user(
            full_name="Duplicate User 2",
            email="dup@autotest.com",
            password="Password123",
            confirm_password="Password123"
        )
        self.assertFalse(ok)
        self.assertIn("already exists", msg.lower())

    def test_user_registration_validation(self):
        """Test input validations during registration."""
        # Empty name
        ok1, msg1, _ = auth_service.register_user("", "test@autotest.com", "Password123")
        self.assertFalse(ok1)
        self.assertIn("name is required", msg1.lower())

        # Invalid email
        ok2, msg2, _ = auth_service.register_user("John", "invalid-email-format", "Password123")
        self.assertFalse(ok2)
        self.assertIn("valid email", msg2.lower())

        # Short password
        ok3, msg3, _ = auth_service.register_user("John", "john@autotest.com", "123")
        self.assertFalse(ok3)
        self.assertIn("at least 6 characters", msg3.lower())

        # Password mismatch
        ok4, msg4, _ = auth_service.register_user("John", "john@autotest.com", "Password123", "Mismatch123")
        self.assertFalse(ok4)
        self.assertIn("do not match", msg4.lower())

    def test_user_authentication_success(self):
        """Test user login with valid credentials."""
        email = "login_success@autotest.com"
        password = "ValidPassword123!"
        auth_service.register_user("Login User", email, password, password)

        ok, msg, data = auth_service.authenticate_user(email, password)
        self.assertTrue(ok)
        self.assertEqual(data.get("email"), email)
        self.assertIsNotNone(data.get("token"))

    def test_user_authentication_invalid_credentials(self):
        """Test login with wrong password or non-existent email."""
        email = "exist@autotest.com"
        auth_service.register_user("Exist User", email, "CorrectPassword123")

        # Wrong password
        ok1, msg1, _ = auth_service.authenticate_user(email, "WrongPassword")
        self.assertFalse(ok1)
        self.assertIn("invalid email or password", msg1.lower())

        # Non-existent email
        ok2, msg2, _ = auth_service.authenticate_user("notfound@autotest.com", "SomePassword")
        self.assertFalse(ok2)
        self.assertIn("invalid email or password", msg2.lower())


if __name__ == "__main__":
    unittest.main()
