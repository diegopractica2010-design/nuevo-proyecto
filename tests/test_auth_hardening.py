import unittest
from jose import jwt
from fastapi.testclient import TestClient

from backend.auth import ALGORITHM, SECRET_KEY, AuthService, TokenService, hash_token, pwd_context
from backend.db import SessionLocal, reset_db
from backend.infrastructure.cache.cache import cache_get, set_cache_client
from backend.infrastructure.db.models import UserRecord
from backend.models_auth import UserCreate, validate_password_strength
from backend.main import app

VALID_PASSWORD = "StrongPass123!"
NEW_PASSWORD = "BetterPass456!"


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value
        self.ttls[key] = ex
        return True

    def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self.values:
                removed += 1
                self.values.pop(key, None)
                self.ttls.pop(key, None)
        return removed


class PasswordPolicyTests(unittest.TestCase):
    def test_valid_password_has_no_failures(self):
        self.assertEqual(validate_password_strength(VALID_PASSWORD), [])

    def test_missing_uppercase(self):
        self.assertIn("contain an uppercase letter", validate_password_strength("strongpass123!"))

    def test_missing_number(self):
        self.assertIn("contain a number", validate_password_strength("StrongPassword!"))

    def test_missing_special(self):
        self.assertTrue(
            any(
                "special character" in failure
                for failure in validate_password_strength("StrongPass123")
            )
        )

    def test_too_short(self):
        self.assertIn("be at least 12 characters", validate_password_strength("Short1!"))

    def test_multiple_failures_are_reported_together(self):
        with self.assertRaises(ValueError) as exc_info:
            UserCreate(username="alice", email="alice@example.com", password="short")
        message = str(exc_info.exception)
        self.assertIn("be at least 12 characters", message)
        self.assertIn("contain an uppercase letter", message)
        self.assertIn("contain a number", message)
        self.assertIn("special character", message)


class AuthHardeningFlowTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        self.redis = FakeRedis()
        set_cache_client(self.redis)
        self.client = TestClient(app)

    def tearDown(self):
        set_cache_client(None)

    def _create_user(
        self, username="alice", email="alice@example.com", password=VALID_PASSWORD, *, verified=True
    ):
        user = AuthService.create_user(username, email, password)
        if verified:
            AuthService.verify_email(username)
        return user

    def test_email_verification_marks_user_verified_and_blocks_unverified_users(self):
        response = self.client.post(
            "/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_verified"])

        login = self.client.post(
            "/auth/login", json={"username": "alice", "password": VALID_PASSWORD}
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["access_token"]

        blocked = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json(), {"detail": "Email not verified"})

        verification_token = TokenService.create_email_verification_token("alice")
        verified = self.client.get(f"/auth/verify?token={verification_token}")
        self.assertEqual(verified.status_code, 200)

        with SessionLocal() as session:
            user = session.get(UserRecord, "alice")
            self.assertTrue(user.is_verified)

        allowed_login = self.client.post(
            "/auth/login", json={"username": "alice", "password": VALID_PASSWORD}
        )
        allowed = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {allowed_login.json()['access_token']}"},
        )
        self.assertEqual(allowed.status_code, 200)

    def test_jwt_blacklist_denies_access_after_logout(self):
        self._create_user()
        login = self.client.post(
            "/auth/login", json={"username": "alice", "password": VALID_PASSWORD}
        )
        token = login.json()["access_token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        logout = self.client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(logout.status_code, 204)
        self.assertIn(f"jwt:blacklist:{payload['jti']}", self.redis.values)

        denied = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(denied.status_code, 401)

    def test_password_reset_creates_redis_entry_updates_hash_and_cannot_be_reused(self):
        self._create_user(email="Alice@Example.com")

        forgot = self.client.post("/auth/forgot-password", json={"email": "alice@example.com"})
        self.assertEqual(forgot.status_code, 200)
        self.assertEqual(forgot.json(), {"detail": "If that email exists, a reset link was sent."})
        self.assertIn("pwd_reset:alice", self.redis.values)

        token = TokenService.create_password_reset_token("alice")
        TokenService.store_password_reset_token("alice", token)
        self.assertEqual(cache_get("pwd_reset:alice"), hash_token(token))

        reset = self.client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": NEW_PASSWORD},
        )
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.json(), {"detail": "Password updated. Please log in."})
        self.assertNotIn("pwd_reset:alice", self.redis.values)

        reused = self.client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "AnotherPass789!"},
        )
        self.assertEqual(reused.status_code, 401)

        with SessionLocal() as session:
            user = session.get(UserRecord, "alice")
            self.assertTrue(pwd_context.verify(NEW_PASSWORD, user.hashed_password))


if __name__ == "__main__":
    unittest.main()
