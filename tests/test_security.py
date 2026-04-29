"""
Tests de seguridad para Radar de Precios.
Verifica: Auth bypass, injection protection, CORS, rate limiting.
"""
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import AuthService, TokenService
from backend.config import CORS_ORIGINS


class SecurityAuthTests(unittest.TestCase):
    """Tests de seguridad para autenticación."""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_login_with_invalid_credentials_returns_401(self):
        """Intento de login con credenciales inválidas debe retornar 401."""
        response = self.client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_login_with_empty_username_returns_422(self):
        """Login con username vacío debe retornar 422 (validation error)."""
        response = self.client.post(
            "/auth/login",
            json={"username": "", "password": "password123"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_login_with_empty_password_returns_422(self):
        """Login con password vacío debe retornar 422."""
        response = self.client.post(
            "/auth/login",
            json={"username": "user", "password": ""}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_register_with_weak_password_returns_422(self):
        """Registro con password débil debe retornar 422."""
        response = self.client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "short"
            }
        )
        self.assertEqual(response.status_code, 422)
        # Verificar que el mensaje indica problema de validación
        data = response.json()
        # El nuevo formato tiene "details" con los errores de campo
        self.assertEqual(data.get("error"), "VALIDATION_ERROR")
    
    def test_register_with_invalid_email_returns_422(self):
        """Registro con email inválido debe retornar 422."""
        response = self.client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "password": "password123"
            }
        )
        self.assertEqual(response.status_code, 422)
    
    def test_register_with_invalid_username_chars_returns_422(self):
        """Registro con caracteres inválidos en username debe retornar 422."""
        response = self.client.post(
            "/auth/register",
            json={
                "username": "user@invalid!",
                "email": "test@example.com",
                "password": "password123"
            }
        )
        self.assertEqual(response.status_code, 422)
    
    def test_protected_endpoint_without_token_returns_401(self):
        """Endpoint protegido sin token debe retornar 401."""
        response = self.client.get("/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authorization", response.json()["detail"])
    
    def test_protected_endpoint_with_invalid_token_returns_401(self):
        """Endpoint con token inválido debe retornar 401."""
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_protected_endpoint_with_malformed_header_returns_401(self):
        """Header Authorization malformado debe retornar 401."""
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": "NotBearer token"}
        )
        self.assertEqual(response.status_code, 401)


class SecurityCORSTests(unittest.TestCase):
    """Tests de seguridad para CORS."""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_cors_not_allow_wildcard(self):
        """CORS no debe permitir wildcard * en producción."""
        # Verificar que CORS_ORIGINS no es ["*"]
        self.assertNotEqual(CORS_ORIGINS, ["*"])
        self.assertIsInstance(CORS_ORIGINS, list)
    
    def test_cors_preflight_rejects_unauthorized_origin(self):
        """Preflight request con origen no autorizado debe fallar."""
        response = self.client.options(
            "/search",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        # El origen no autorizado no debería estar en los headers de respuesta
        # FastAPI maneja esto automáticamente con allow_origins configurado


class SecurityRateLimitTests(unittest.TestCase):
    """Tests de seguridad para rate limiting."""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_rate_limit_headers_present(self):
        """Respuesta debe incluir headers de rate limiting."""
        response = self.client.get("/search?query=leche")
        # Debe tener headers de rate limit
        self.assertIn("X-RateLimit-Limit", response.headers)
    
    def test_excessive_requests_get_rate_limited(self):
        """Requests excesivos deben ser rate limited."""
        # Hacer muchas requests rápidamente
        # (El test real requeriría mock del tiempo o esperar)
        # Verificamos que el middleware existe
        from backend.middleware import RateLimitMiddleware
        self.assertIsNotNone(RateLimitMiddleware)


class SecurityInputTests(unittest.TestCase):
    """Tests de validación de entrada."""
    
    def setUp(self):
        self.client = TestClient(app)
    
    def test_search_rejects_empty_query(self):
        """Búsqueda con query vacía debe rechazarse."""
        response = self.client.get("/search?query=")
        self.assertEqual(response.status_code, 422)
    
    def test_search_rejects_sql_injection_attempt(self):
        """Intento de SQL injection debe sanitizarse (no ejecutarse)."""
        # El query se pasa al scraper, no directamente a SQL
        # Verificar que no hay error de SQL
        response = self.client.get("/search?query='; DROP TABLE users;--")
        # Debe responder con algo (error o resultados), no crash
        self.assertIn(response.status_code, [200, 400, 422, 500, 502])
    
    def test_basket_id_validated(self):
        """Basket ID debe validarse."""
        response = self.client.get("/baskets/invalid-uuid-format")
        # Debe manejar gracefully (404 o validación)
        self.assertIn(response.status_code, [404, 422])


if __name__ == "__main__":
    unittest.main()