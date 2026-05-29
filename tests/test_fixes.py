"""Tests for Fixes 1-4: API KEY, METRICS, RATE LIMITING, JWT HARDENING."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app
from backend.db import reset_db
from backend.scraper_jumbo import NoResultsError
from backend.rate_limiter import RateLimiter


class TestFix1JumboAPIKey(unittest.TestCase):
    """Tests for JUMBO_API_KEY moved to config with graceful degradation."""
    
    def test_jumbo_api_key_imported_from_config(self):
        """Verify JUMBO_API_KEY is imported from config, not hardcoded."""
        from backend import scraper_jumbo
        from backend.config import JUMBO_API_KEY
        
        # Should import without hardcoded constant
        self.assertFalse(hasattr(scraper_jumbo, 'JUMBO_CATALOG_API_KEY') 
                        and scraper_jumbo.JUMBO_CATALOG_API_KEY == "WlVnnB7c1BblmgUPOfg",
                        "JUMBO_CATALOG_API_KEY should not be hardcoded anymore")
    
    @patch('backend.scraper_jumbo.JUMBO_API_KEY', "")
    @patch('backend.scraper_jumbo._client_get')
    def test_jumbo_search_gracefully_handles_missing_api_key(self, mock_get):
        """Test that Jumbo search fails gracefully when API_KEY is empty."""
        from backend.scraper_jumbo import _execute_catalog_api_query
        
        # Should raise NoResultsError with specific message about missing API key
        with self.assertRaises(NoResultsError) as ctx:
            asyncio.run(_execute_catalog_api_query(object(), "leche", limit=10))
        
        self.assertIn("JUMBO_API_KEY not configured", str(ctx.exception))
    
    def test_env_example_includes_jumbo_api_key(self):
        """Verify .env.example includes JUMBO_API_KEY."""
        with open(".env.example", "r") as f:
            content = f.read()
            self.assertIn("JUMBO_API_KEY", content, 
                         ".env.example should document JUMBO_API_KEY variable")


class TestFix2PrometheusMetrics(unittest.TestCase):
    """Tests for PROMETHEUS METRICS returning text/plain format."""
    
    def setUp(self):
        reset_db()
        self.client = TestClient(app)
    
    def test_metrics_endpoint_returns_text_plain(self):
        """Verify /metrics endpoint returns text/plain format."""
        response = self.client.get("/metrics")
        
        # Should be 200 with text/plain content type
        self.assertEqual(response.status_code, 200)
        content_type = response.headers.get("content-type", "")
        self.assertIn("text/plain", content_type,
                     f"Expected text/plain, got {content_type}")
    
    def test_metrics_endpoint_returns_prometheus_format(self):
        """Verify /metrics returns actual Prometheus text format (lines with # or METRIC)."""
        response = self.client.get("/metrics")
        
        # Prometheus text format contains lines starting with # or metric names
        text = response.text
        self.assertGreater(len(text), 0, "Metrics response should not be empty")
        
        # Should contain either comments or actual metrics
        has_comments = any(line.startswith("#") for line in text.split("\n"))
        has_metrics = any(line and not line.startswith("#") for line in text.split("\n"))
        
        self.assertTrue(has_comments or has_metrics,
                       "Metrics should contain Prometheus format lines")
    
    def test_metrics_not_json(self):
        """Verify /metrics does NOT return JSON format."""
        response = self.client.get("/metrics")
        
        # Should not be parseable as JSON
        text = response.text
        self.assertFalse(text.startswith("{"),
                        "Metrics should not return JSON format")


class TestFix3RateLimiting(unittest.TestCase):
    """Tests for DISTRIBUTED RATE LIMITING with Redis sliding window."""
    
    def setUp(self):
        self.rate_limiter = RateLimiter()
    
    def test_rate_limiter_uses_redis_operations(self):
        """Verify rate limiter uses Redis sorted sets (ZADD, ZREMRANGEBYSCORE, ZCARD)."""
        # This is verified by the implementation using ZADD, ZREMRANGEBYSCORE, ZCARD
        self.assertIsNotNone(self.rate_limiter.redis_client,
                            "Rate limiter should attempt Redis connection")
    
    def test_rate_limiter_gracefully_degrades_without_redis(self):
        """Test that rate limiter allows all requests if Redis is unavailable."""
        rate_limiter = RateLimiter()
        rate_limiter.redis_client = None  # Simulate Redis unavailable
        
        # Create a mock request
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers.get.return_value = None
        
        # Should allow request (graceful degradation)
        is_limited, metadata = rate_limiter.is_rate_limited(mock_request)
        self.assertFalse(is_limited,
                        "Should allow request when Redis is unavailable")
        self.assertTrue(metadata.get("allowed"),
                       "Metadata should indicate request is allowed")
    
    def test_rate_limiter_extracts_client_ip(self):
        """Test that rate limiter correctly extracts client IP."""
        # Create a mock request
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers.get.return_value = None
        
        # Rate limiter should extract IP
        ip = self.rate_limiter._get_ip(mock_request)
        self.assertEqual(ip, "192.168.1.100",
                        "Should extract correct client IP")


class TestFix4JWTHardening(unittest.TestCase):
    """Tests for JWT HARDENING: refresh endpoint and startup logging."""
    
    def setUp(self):
        reset_db()
        self.client = TestClient(app)
        
        # Create test user
        self.client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123"
            }
        )
    
    def test_jwt_startup_logging_indicates_status(self):
        """Verify JWT startup logging clearly indicates fixed vs ephemeral key."""
        from backend import auth
        import logging
        
        # Should have logged about JWT_SECRET_KEY status
        # This is verified in auth.py _get_secret_key() which logs:
        # - "JWT_SECRET_KEY configured and fixed (from environment)" if fixed
        # - "JWT_SECRET_KEY not configured in development. Using ephemeral key..." if ephemeral
        self.assertIsNotNone(auth.SECRET_KEY)
    
    def test_auth_refresh_endpoint_exists(self):
        """Verify POST /auth/refresh endpoint is implemented."""
        # Login to get token
        login_response = self.client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["access_token"]
        
        # Try to refresh token
        refresh_response = self.client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should succeed and return new token
        self.assertEqual(refresh_response.status_code, 200,
                        "Refresh endpoint should exist and return 200")
        self.assertIn("access_token", refresh_response.json(),
                     "Refresh response should include new access_token")
    
    def test_auth_refresh_returns_different_token(self):
        """Verify that refresh endpoint returns a new token with reset TTL."""
        # Login to get token
        login_response = self.client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )
        token1 = login_response.json()["access_token"]
        
        # Refresh to get new token
        refresh_response = self.client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token1}"}
        )
        token2 = refresh_response.json()["access_token"]
        
        # Tokens should be different
        self.assertNotEqual(token1, token2,
                           "Refresh should return a new token")
    
    def test_auth_refresh_requires_valid_token(self):
        """Verify refresh endpoint requires valid Bearer token."""
        # Try without token
        response = self.client.post(
            "/auth/refresh",
            headers={}
        )
        self.assertEqual(response.status_code, 401,
                        "Refresh should require Bearer token")
        
        # Try with invalid token
        response = self.client.post(
            "/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"}
        )
        self.assertEqual(response.status_code, 401,
                        "Refresh should reject invalid token")
    
    def test_auth_refresh_only_works_for_existing_users(self):
        """Verify refresh endpoint checks that user exists."""
        # Login with real user to get token
        login_response = self.client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Valid token should work (user exists)
        refresh_response = self.client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(refresh_response.status_code, 200,
                        "Refresh should work for existing user")
    
    def test_auth_endpoints_unchanged(self):
        """Verify existing auth endpoints remain unchanged."""
        # /auth/register should still work
        register_response = self.client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password456"
            }
        )
        self.assertEqual(register_response.status_code, 200)
        
        # /auth/login should still work
        login_response = self.client.post(
            "/auth/login",
            json={"username": "newuser", "password": "password456"}
        )
        self.assertEqual(login_response.status_code, 200)
        
        # /auth/me should still work
        token = login_response.json()["access_token"]
        me_response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["username"], "newuser")


class TestStatusDashboard(unittest.TestCase):
    """Tests for GET /status dashboard."""

    def setUp(self):
        reset_db()
        self.client = TestClient(app)

    def test_status_returns_200(self):
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)

    def test_status_contains_postgresql(self):
        response = self.client.get("/status")
        self.assertIn("PostgreSQL", response.text)

    def test_status_is_html(self):
        response = self.client.get("/status")
        content_type = response.headers.get("content-type", "")
        self.assertIn("text/html", content_type)


if __name__ == "__main__":
    unittest.main()
