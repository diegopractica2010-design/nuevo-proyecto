"""
HTML Structure Monitoring - FASE A

Monitorea cambios en la estructura HTML de tiendas.
Si cambia significativamente, alerta para evitar parser failures.

Estrategia:
1. Hacer snapshot periódico del HTML de búsqueda
2. Comparar con snapshot anterior
3. Si cambio > threshold, alertar
4. Guardar histórico de snapshots para debugging
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from backend.config import (
    DATA_DIR,
    REQUEST_TIMEOUT,
    BROWSER_HEADERS,
)

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = DATA_DIR / "parser_snapshots"
PARSER_HISTORY_FILE = SNAPSHOT_DIR / "parser_history.json"


def _ensure_snapshot_dir():
    """Create snapshot directory if doesn't exist."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _get_html_hash(html: str) -> str:
    """Get SHA256 hash of HTML content."""
    return hashlib.sha256(html.encode()).hexdigest()[:16]


def _get_snapshot_filename(store: str, date: Optional[datetime] = None) -> str:
    """Generate snapshot filename."""
    if date is None:
        date = datetime.now()
    timestamp = date.strftime("%Y%m%d_%H%M%S")
    return f"{store}_snapshot_{timestamp}.html"


def _load_history() -> dict:
    """Load parser change history."""
    _ensure_snapshot_dir()
    if PARSER_HISTORY_FILE.exists():
        try:
            with open(PARSER_HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load parser history: {e}")
    return {}


def _save_history(history: dict):
    """Save parser change history."""
    _ensure_snapshot_dir()
    try:
        with open(PARSER_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save parser history: {e}")


def take_html_snapshot(store: str, query: str = "leche") -> Optional[dict]:
    """
    Take HTML snapshot of a search page.
    
    Returns:
        {
            "store": "lider",
            "timestamp": "2024-04-27T10:30:00",
            "hash": "abc123...",
            "html_file": "path/to/snapshot.html",
            "size_kb": 150,
        }
    """
    try:
        _ensure_snapshot_dir()
        
        # Construct search URL
        if store == "lider":
            url = f"https://super.lider.cl/search?q={query}"
        elif store == "jumbo":
            url = f"https://www.jumbo.cl/busqueda?ft={query}"
        else:
            return None
        
        # Fetch HTML
        logger.info(f"Taking snapshot of {store}...")
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        html = response.text
        html_hash = _get_html_hash(html)
        
        # Save snapshot
        filename = _get_snapshot_filename(store)
        filepath = SNAPSHOT_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        
        snapshot_info = {
            "store": store,
            "timestamp": datetime.now().isoformat(),
            "hash": html_hash,
            "html_file": str(filepath),
            "size_kb": len(html) / 1024,
            "query": query,
        }
        
        logger.info(f"Snapshot saved: {filename} (hash: {html_hash})")
        return snapshot_info
    
    except Exception as e:
        logger.error(f"Failed to take snapshot of {store}: {e}")
        return None


def compare_snapshots(store: str) -> Optional[dict]:
    """
    Compare current snapshot with previous.
    
    Returns:
        {
            "store": "lider",
            "changed": True,
            "severity": "high",  # low|medium|high|critical
            "last_hash": "abc...",
            "current_hash": "xyz...",
            "message": "Structure changed significantly",
            "action": "MANUAL_REVIEW_REQUIRED",
        }
    """
    try:
        history = _load_history()
        
        # Take new snapshot
        current = take_html_snapshot(store)
        if not current:
            return None
        
        current_hash = current["hash"]
        
        # Get last snapshot hash
        last_hash = history.get(f"{store}_last_hash")
        
        if not last_hash:
            logger.info(f"No previous snapshot for {store}. Setting baseline.")
            history[f"{store}_last_hash"] = current_hash
            history[f"{store}_last_snapshot"] = current
            _save_history(history)
            return {
                "store": store,
                "changed": False,
                "message": "Baseline snapshot set",
            }
        
        # Compare
        changed = current_hash != last_hash
        
        if changed:
            logger.warning(f"HTML structure changed for {store}!")
            logger.warning(f"  Previous hash: {last_hash}")
            logger.warning(f"  Current hash: {current_hash}")
            
            # Determine severity (placeholder)
            # TODO: Implement content-aware comparison (CSS selectors, element count, etc.)
            severity = "high"  # Conservative: treat all changes as high
            
            result = {
                "store": store,
                "changed": True,
                "severity": severity,
                "last_hash": last_hash,
                "current_hash": current_hash,
                "message": f"HTML structure changed for {store}",
                "action": "MANUAL_REVIEW_REQUIRED",
            }
            
            # Update history
            history[f"{store}_last_hash"] = current_hash
            history[f"{store}_last_snapshot"] = current
            history[f"{store}_last_change"] = {
                "timestamp": datetime.now().isoformat(),
                "previous_hash": last_hash,
                "new_hash": current_hash,
                "severity": severity,
            }
            _save_history(history)
            
            return result
        else:
            logger.debug(f"HTML structure unchanged for {store}")
            return {
                "store": store,
                "changed": False,
                "message": "No structural changes detected",
            }
    
    except Exception as e:
        logger.error(f"Failed to compare snapshots for {store}: {e}")
        return None


def get_parser_status() -> dict:
    """Get current parser status for all stores."""
    history = _load_history()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "lider": {
            "last_hash": history.get("lider_last_hash"),
            "last_change": history.get("lider_last_change"),
        },
        "jumbo": {
            "last_hash": history.get("jumbo_last_hash"),
            "last_change": history.get("jumbo_last_change"),
        },
        "snapshot_dir": str(SNAPSHOT_DIR),
    }


# Celery task (placeholder - usar en backend.tasks)
def monitor_html_changes() -> dict:
    """
    Periodic task to monitor HTML changes.
    
    Called from: celery beat scheduler (backend/celery_app.py)
    Frequency: Every 6 hours (TO BE CONFIGURED)
    """
    try:
        logger.info("Starting HTML structure monitoring...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "stores": {},
        }
        
        for store in ["lider", "jumbo"]:
            try:
                result = compare_snapshots(store)
                results["stores"][store] = result
                
                if result and result.get("changed"):
                    logger.warning(
                        f"ALERT: {store} HTML structure changed! "
                        f"Severity: {result.get('severity')}"
                    )
                    # TODO: Send alert (email, Slack, Sentry)
            
            except Exception as e:
                logger.error(f"Monitor failed for {store}: {e}")
                results["stores"][store] = {"error": str(e)}
        
        logger.info("HTML structure monitoring completed")
        return results
    
    except Exception as e:
        logger.error(f"HTML monitoring task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }
