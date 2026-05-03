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
