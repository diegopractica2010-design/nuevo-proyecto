"""Tests de regresion de seguridad. Si alguno falla, hay una vulnerabilidad activa."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_baskets_sin_token_no_retorna_200():
    """GET /baskets sin autenticacion NO debe retornar 200 con datos."""
    response = client.get("/baskets")
    assert response.status_code in (401, 403, 422), (
        f"GET /baskets sin token retorno {response.status_code}. "
        "Hay una fuga de datos: cualquier persona puede ver todas las canastas."
    )


def test_baskets_con_token_invalido_retorna_401():
    """Un JWT invalido debe ser rechazado."""
    response = client.get("/baskets", headers={"Authorization": "Bearer token_completamente_falso"})
    assert response.status_code in (401, 403)


def test_admin_backup_sin_token_retorna_401_o_403():
    """El endpoint de backup no debe ser accesible sin autenticacion."""
    response = client.post("/admin/backup")
    assert response.status_code in (401, 403, 422)


def test_headers_de_seguridad_presentes():
    """La respuesta debe incluir headers de seguridad basicos."""
    response = client.get("/")
    headers = response.headers
    assert "x-frame-options" in headers, "Falta X-Frame-Options (riesgo clickjacking)"
    assert "x-content-type-options" in headers, "Falta X-Content-Type-Options"
    assert "content-security-policy" in headers, "Falta Content-Security-Policy"


def test_csp_no_tiene_unsafe_eval():
    """El CSP no debe permitir eval()."""
    response = client.get("/")
    csp = response.headers.get("content-security-policy", "")
    script_src = [part for part in csp.split(";") if "script-src" in part]
    if script_src:
        assert "unsafe-eval" not in script_src[0], (
            "El CSP tiene 'unsafe-eval' en script-src. "
            "Esto permite ejecutar eval() y anula la proteccion contra XSS."
        )


class _FakeSortedSetPipeline:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.operations = []

    def zremrangebyscore(self, key, minimum, maximum):
        self.operations.append(("zremrangebyscore", key, minimum, maximum))
        return self

    def zcard(self, key):
        self.operations.append(("zcard", key))
        return self

    def zadd(self, key, mapping):
        self.operations.append(("zadd", key, mapping))
        return self

    def expire(self, key, seconds):
        self.operations.append(("expire", key, seconds))
        return self

    def execute(self):
        results = []
        for operation in self.operations:
            name = operation[0]
            if name == "zremrangebyscore":
                _, key, minimum, maximum = operation
                self.redis_client.zsets[key] = [
                    item
                    for item in self.redis_client.zsets.get(key, [])
                    if not (minimum <= item[1] <= maximum)
                ]
                results.append(True)
            elif name == "zcard":
                _, key = operation
                results.append(len(self.redis_client.zsets.get(key, [])))
            elif name == "zadd":
                _, key, mapping = operation
                bucket = self.redis_client.zsets.setdefault(key, [])
                for member, score in mapping.items():
                    bucket.append((member, score))
                results.append(len(mapping))
            elif name == "expire":
                _, key, seconds = operation
                self.redis_client.ttls[key] = seconds
                results.append(True)
        return results


class _FakeSortedSetRedis:
    def __init__(self):
        self.zsets = {}
        self.ttls = {}

    def pipeline(self):
        return _FakeSortedSetPipeline(self)

    def zrange(self, key, start, end, withscores=False):
        values = sorted(self.zsets.get(key, []), key=lambda item: item[1])
        selected = values[start : end + 1]
        return selected if withscores else [member for member, _ in selected]


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), default)


class _Request:
    def __init__(self, *, ip="10.0.0.1", token=None):
        self.client = type("Client", (), {"host": ip})()
        self.headers = _Headers()
        if token:
            self.headers["authorization"] = f"Bearer {token}"


def test_cors_allowed_origin_returns_authorization_headers():
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin_has_no_authorization_headers():
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_production_requires_explicit_cors_origins(monkeypatch):
    from backend.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    try:
        Settings()
    except RuntimeError as exc:
        assert str(exc) == "CORS_ORIGINS must be set explicitly in production"
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("Production settings without CORS_ORIGINS should fail")


def test_wildcard_cors_origin_rejected_with_credentials(monkeypatch):
    from pydantic import ValidationError

    from backend.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    try:
        Settings()
    except ValidationError as exc:
        assert "Wildcard origins cannot be used with credentials" in str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("Wildcard CORS origin with credentials should fail")


def test_authenticated_rate_limit_uses_user_bucket_not_ip_bucket():
    from backend.auth import AuthService, TokenService
    from backend.db import reset_db
    from backend.rate_limiter import RateLimiter

    reset_db()
    AuthService.create_user("ratelimited", "ratelimited@example.com", "StrongPass123!")
    AuthService.verify_email("ratelimited")
    token = TokenService.create_access_token({"sub": "ratelimited"})

    limiter = RateLimiter(requests_per_minute=1, auth_requests_per_minute=2)
    limiter.redis_client = _FakeSortedSetRedis()
    request = _Request(ip="203.0.113.10", token=token)

    first_limited, first_metadata = limiter.is_rate_limited(request)
    second_limited, second_metadata = limiter.is_rate_limited(request)
    third_limited, third_metadata = limiter.is_rate_limited(request)

    assert not first_limited
    assert not second_limited
    assert third_limited
    assert first_metadata["key"] == "rl:user:ratelimited"
    assert second_metadata["bucket_type"] == "user"
    assert third_metadata["retry_after"] >= 1
    assert "rl:user:ratelimited" in limiter.redis_client.zsets
    assert "rl:ip:203.0.113.10" not in limiter.redis_client.zsets


def test_unauthenticated_rate_limit_still_uses_ip_bucket():
    from backend.rate_limiter import RateLimiter

    limiter = RateLimiter(requests_per_minute=1, auth_requests_per_minute=2)
    limiter.redis_client = _FakeSortedSetRedis()
    request = _Request(ip="198.51.100.20")

    first_limited, first_metadata = limiter.is_rate_limited(request)
    second_limited, second_metadata = limiter.is_rate_limited(request)

    assert not first_limited
    assert second_limited
    assert first_metadata["key"] == "rl:ip:198.51.100.20"
    assert second_metadata["bucket_type"] == "ip"
    assert second_metadata["retry_after"] >= 1


def test_rate_limit_middleware_returns_429_with_retry_after_header():
    import anyio
    from starlette.responses import Response

    from backend.middleware import RateLimitMiddleware

    class AlwaysLimited:
        def is_rate_limited(self, request):
            return True, {
                "allowed": False,
                "limit": 1,
                "window": 60,
                "retry_after": 42,
                "ip": "198.51.100.20",
            }

    async def run_dispatch():
        middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
        middleware.rate_limiter = AlwaysLimited()
        request = type("Request", (), {"url": type("Url", (), {"path": "/stores"})()})()
        return await middleware.dispatch(request, lambda request: Response("ok"))

    response = anyio.run(run_dispatch)

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
