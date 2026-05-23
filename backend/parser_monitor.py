from __future__ import annotations

import hashlib
import json
import logging
import os
import smtplib
from datetime import UTC, datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from backend.config import BROWSER_HEADERS, DATA_DIR, REQUEST_TIMEOUT, STORE_SSL_VERIFY
from backend.metrics import scraper_health_failures


logger = logging.getLogger(__name__)

SNAPSHOT_DIR = DATA_DIR / "parser_snapshots"
PRODUCT_SNAPSHOT_DIR = DATA_DIR / "snapshots"
STATE_FILE = SNAPSHOT_DIR / "parser_state.json"

CONTROL_QUERIES = {
    "lider": "arroz",
    "jumbo": "arroz",
}

KNOWN_PARSE_STRATEGIES = {
    "lider": {"next_data", "graphql", "html_fallback"},
    "jumbo": {"catalog_api"},
}


def run_full_check() -> dict[str, Any]:
    """Ejecuta un check real de los scrapers y guarda el estado."""
    result = {
        "timestamp": datetime.now(UTC).isoformat(),
        "stores": {},
    }

    for store, query in CONTROL_QUERIES.items():
        result["stores"][store] = check_store(store, query)

    state = _load_state()
    state["last_check"] = result["timestamp"]
    state["last_result"] = result
    _save_state(state)
    return result


def check_store(store: str, query: str = "arroz") -> dict[str, Any]:
    started = datetime.now(UTC)
    issues: list[str] = []
    product_count = 0
    structure_changed = False
    structure_detail = ""
    parse_strategy = "unknown"

    try:
        if store == "lider":
            from backend.scraper import search_lider

            result = search_lider(query=query, limit=10)
            parse_strategy = _normalize_parse_strategy(store, result.parse_strategy)
        elif store == "jumbo":
            from backend.scraper_jumbo import search_jumbo

            result = search_jumbo(query=query, limit=10)
            parse_strategy = _normalize_parse_strategy(store, result.parse_strategy)
        else:
            raise ValueError(f"Tienda desconocida: {store}")

        products = getattr(result, "products", []) or []
        product_count = len(products)

        if product_count == 0:
            issues.append("El scraper no extrajo productos")

        first_product = products[0] if products else None
        first_price = _product_price(first_product)
        if first_price is None or not 500 <= first_price <= 10000:
            issues.append(f"Precio canonico fuera de rango: {first_price}")

        if parse_strategy not in KNOWN_PARSE_STRATEGIES[store]:
            issues.append(f"Parse strategy desconocida: {parse_strategy}")

        if isinstance(first_product, dict):
            structure_changed, structure_detail = _snapshot_product_keys(store, first_product)
            if structure_changed:
                logger.warning("Drift estructural en %s: %s", store, structure_detail)

        status = "degraded" if issues else "ok"
        store_result = {
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_seconds": (datetime.now(UTC) - started).total_seconds(),
            "product_count": product_count,
            "parse_strategy": parse_strategy,
            "first_product": first_product,
            "first_price": first_price,
            "issues": issues,
            "structure_changed": structure_changed,
            "structure_detail": structure_detail,
        }

        if status == "degraded":
            scraper_health_failures.labels(store=store).inc()
            logger.error("Scraper health degraded for %s: %s", store, issues)
            store_result["alert_sent"] = _send_alert(_build_alert_message(store, store_result))

        return store_result
    except Exception as exc:
        logger.error("Parser check failed for %s: %s", store, exc, exc_info=True)
        scraper_health_failures.labels(store=store).inc()
        store_result = {
            "status": "down",
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_seconds": (datetime.now(UTC) - started).total_seconds(),
            "product_count": product_count,
            "issues": [str(exc)],
            "parse_strategy": parse_strategy,
            "structure_changed": structure_changed,
            "structure_detail": structure_detail,
            "alert_reason": "Excepcion durante el check",
        }
        store_result["alert_sent"] = _send_alert(_build_alert_message(store, store_result))
        return store_result


def get_status() -> dict[str, Any]:
    """Retorna el ultimo estado guardado por run_full_check."""
    state = _load_state()
    last_result = state.get("last_result")
    if isinstance(last_result, dict):
        return {
            "status": _aggregate_status(last_result),
            "last_check": state.get("last_check"),
            **last_result,
        }
    return {
        "status": "unknown",
        "last_check": None,
        "stores": {},
        "snapshot_dir": str(SNAPSHOT_DIR),
    }


def get_parser_status() -> dict[str, Any]:
    """Compatibilidad con endpoints legacy de monitoreo."""
    return get_status()


def monitor_html_changes() -> dict[str, Any]:
    """Compatibilidad con la tarea legacy."""
    return run_full_check()


def compare_snapshots(store: str) -> dict[str, Any] | None:
    """Compatibilidad: toma HTML actual y compara hashes guardados."""
    try:
        html = _fetch_search_html(store, CONTROL_QUERIES.get(store, "leche"))
        changed, detail = _check_structure_changed(store, html)
        return {
            "store": store,
            "changed": changed,
            "message": detail or "No structural changes detected",
        }
    except Exception as exc:
        logger.warning("compare_snapshots failed for %s: %s", store, exc)
        return None


def take_html_snapshot(store: str, query: str = "leche") -> dict[str, Any] | None:
    try:
        html = _fetch_search_html(store, query)
        path = _save_latest_snapshot(store, html)
        return {
            "store": store,
            "timestamp": datetime.now(UTC).isoformat(),
            "hash": _hash_text(html),
            "html_file": str(path),
            "size_kb": len(html) / 1024,
            "query": query,
        }
    except Exception as exc:
        logger.error("Failed to take snapshot of %s: %s", store, exc)
        return None


def _fetch_search_html(store: str, query: str) -> str:
    if store == "lider":
        url = "https://super.lider.cl/search"
        params = {"q": query}
    elif store == "jumbo":
        url = "https://www.jumbo.cl/busqueda"
        params = {"ft": query}
    else:
        raise ValueError(f"Tienda desconocida: {store}")

    response = requests.get(
        url,
        params=params,
        headers=BROWSER_HEADERS,
        timeout=REQUEST_TIMEOUT,
        verify=STORE_SSL_VERIFY,
    )
    response.raise_for_status()
    return response.text


def _save_latest_snapshot(store: str, html: str) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    latest = SNAPSHOT_DIR / f"{store}_latest.html"
    latest.write_text(html, encoding="utf-8")
    stamped = SNAPSHOT_DIR / f"{store}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.html"
    stamped.write_text(html, encoding="utf-8")
    return latest


def _check_structure_changed(store: str, html: str) -> tuple[bool, str]:
    try:
        html_hash = _hash_text(html)
        next_data_shape_hash = _extract_next_data_shape_hash(html)
        state = _load_state()
        prev_html_hash = state.get(f"{store}.html_hash")
        prev_next_shape_hash = state.get(f"{store}.next_data_shape_hash")

        changed = False
        detail = ""
        if prev_html_hash and prev_html_hash != html_hash:
            changed = True
            detail = f"HTML hash {prev_html_hash} -> {html_hash}"
            if next_data_shape_hash:
                if prev_next_shape_hash is None:
                    detail += " (__NEXT_DATA__ shape baseline creado)"
                    changed = False
                elif prev_next_shape_hash != next_data_shape_hash:
                    detail += (
                        f" (__NEXT_DATA__ shape: {prev_next_shape_hash} -> "
                        f"{next_data_shape_hash})"
                    )
                else:
                    detail += " (__NEXT_DATA__ shape sin cambios)"
                    changed = False

        state[f"{store}.html_hash"] = html_hash
        if next_data_shape_hash:
            state[f"{store}.next_data_shape_hash"] = next_data_shape_hash
        _save_state(state)
        return changed, detail
    except Exception as exc:
        logger.warning("Structure check failed for %s: %s", store, exc)
        return False, f"check fallo: {exc}"


def _extract_next_data_shape_hash(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if not script or not script.string:
        return None
    try:
        payload = json.loads(script.string)
    except json.JSONDecodeError:
        return _hash_text(script.string)
    signature = _shape_signature(payload)
    return _hash_text(json.dumps(signature, sort_keys=True, ensure_ascii=False))


def _shape_signature(value: Any, depth: int = 0, max_depth: int = 8) -> Any:
    if depth > max_depth:
        return type(value).__name__
    if isinstance(value, dict):
        return {
            key: _shape_signature(child, depth + 1, max_depth)
            for key, child in sorted(value.items(), key=lambda item: item[0])
        }
    if isinstance(value, list):
        if not value:
            return []
        sample = value[:3]
        return [_shape_signature(child, depth + 1, max_depth) for child in sample]
    return type(value).__name__


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _aggregate_status(result: dict[str, Any]) -> str:
    stores = result.get("stores", {})
    statuses = [item.get("status") for item in stores.values() if isinstance(item, dict)]
    if any(status == "down" for status in statuses):
        return "down"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return "ok"


def _normalize_parse_strategy(store: str, parse_strategy: str | None) -> str:
    value = str(parse_strategy or "unknown")
    if store == "lider":
        if value in {"lider_graphql", "graphql"}:
            return "graphql"
        if value == "next_data":
            return "next_data"
        if value in {"ld_json", "inline_search", "html", "css_selectors"}:
            return "html_fallback"
    if store == "jumbo" and value in {"vtex_catalog_api", "catalog_api"}:
        return "catalog_api"
    return value


def _product_price(product: Any) -> float | None:
    if isinstance(product, dict):
        raw_price = product.get("price")
    else:
        raw_price = getattr(product, "price", None)
    try:
        return float(raw_price)
    except (TypeError, ValueError):
        return None


def _snapshot_product_keys(store: str, product: dict[str, Any]) -> tuple[bool, str]:
    PRODUCT_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    keys = sorted(product.keys())
    today = datetime.now(UTC).strftime("%Y%m%d")
    path = PRODUCT_SNAPSHOT_DIR / f"{store}-{today}.json"
    path.write_text(
        json.dumps(
            {
                "store": store,
                "timestamp": datetime.now(UTC).isoformat(),
                "keys": keys,
                "sample": product,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    state = _load_state()
    previous = state.get(f"{store}.product_keys")
    state[f"{store}.product_keys"] = keys
    _save_state(state)

    if not isinstance(previous, list):
        return False, "baseline creado"

    missing = sorted(set(previous) - set(keys))
    added = sorted(set(keys) - set(previous))
    if missing or added:
        return True, f"added={added}; missing={missing}"
    return False, "sin cambios"


def _build_alert_message(store: str, result: dict[str, Any]) -> str:
    issues = "\n".join(f"  - {issue}" for issue in result.get("issues", []))
    return (
        "ALERTA RADAR DE PRECIOS\n\n"
        f"Tienda: {store.upper()}\n"
        f"Hora: {result.get('timestamp')}\n"
        f"Estado: {result.get('status', 'desconocido').upper()}\n"
        f"Productos en check de control: {result.get('product_count', '?')}\n\n"
        f"Problemas detectados:\n{issues}\n\n"
        f"Razon de alerta: {result.get('alert_reason', 'No especificada')}\n\n"
        f"Snapshot HTML: data/parser_snapshots/{store}_latest.html"
    )


def _send_alert(message: str) -> bool:
    sent = False

    token = os.getenv("ALERT_TELEGRAM_TOKEN")
    chat_id = os.getenv("ALERT_TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": ""},
                timeout=10,
            )
            if response.ok:
                logger.info("Alerta Telegram enviada")
                sent = True
            else:
                logger.warning("Telegram fallo: %s %s", response.status_code, response.text[:200])
        except Exception as exc:
            logger.warning("Error enviando alerta Telegram: %s", exc)

    email_to = os.getenv("ALERT_EMAIL_TO")
    smtp_host = os.getenv("SMTP_HOST")
    if email_to and smtp_host and not sent:
        try:
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_pass = os.getenv("SMTP_PASSWORD", "")
            from_addr = os.getenv("SMTP_FROM", smtp_user or "alerts@radar.local")

            msg = MIMEText(message)
            msg["Subject"] = "Radar de Precios - Parser Alert"
            msg["From"] = from_addr
            msg["To"] = email_to

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [email_to], msg.as_string())

            logger.info("Alerta email enviada a %s", email_to)
            sent = True
        except Exception as exc:
            logger.warning("Error enviando alerta email: %s", exc)

    if not sent:
        logger.error("ALERTA SIN CANAL CONFIGURADO:\n%s", message)

    return sent


def _load_state() -> dict[str, Any]:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict[str, Any]) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
