"""
Self-contained HTML status dashboard served at GET /status.
No React, no build step — pure HTML/CSS/JS in a Python string.
Auto-refreshes every 10 seconds.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service checks — each returns (status_text, error_message | None)
# ---------------------------------------------------------------------------

def _check_postgres() -> Tuple[str, str | None]:
    try:
        from sqlalchemy import text
        from backend.db import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected", None
    except Exception as exc:
        return "error", str(exc)[:200]


def _check_redis() -> Tuple[str, str | None]:
    try:
        import redis as redis_lib
        from backend.config import REDIS_URL
        r = redis_lib.from_url(REDIS_URL, socket_timeout=2, socket_connect_timeout=2)
        r.ping()
        return "connected", None
    except Exception as exc:
        return "error", str(exc)[:200]


def _check_celery() -> Tuple[str, str | None]:
    try:
        from backend.celery_app import celery_app
        result = celery_app.control.inspect(timeout=2).ping()
        if result:
            return f"{len(result)} worker(s) active", None
        return "no workers", "No active Celery workers found (broker may be down)"
    except Exception as exc:
        return "error", str(exc)[:200]


def _check_prometheus() -> Tuple[str, str | None]:
    try:
        from backend.metrics import get_metrics_response
        data, _ = get_metrics_response()
        size = len(data) if data else 0
        return f"ok ({size:,} bytes)", None
    except Exception as exc:
        return "error", str(exc)[:200]


def _recent_logs(n: int = 5) -> list[str]:
    log_path = Path("data/logs/app.log")
    try:
        if not log_path.exists():
            return ["(log file not found — check data/logs/app.log)"]
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        tail = [ln.rstrip() for ln in lines[-n:]] if lines else []
        return tail if tail else ["(log file is empty)"]
    except Exception as exc:
        return [f"Error reading logs: {exc}"]


def _last_backup() -> str:
    backup_dir = Path("data/backups")
    try:
        if not backup_dir.exists():
            return "no backups yet"
        entries = sorted(backup_dir.iterdir(), reverse=True)
        if not entries:
            return "no backups yet"
        return entries[0].name
    except Exception as exc:
        return f"error: {exc}"


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _color(status: str, error: str | None) -> str:
    if error:
        return "#ff4444"
    if "no worker" in status or "warn" in status:
        return "#ffaa00"
    return "#00ff88"


def _service_card(title: str, status: str, error: str | None) -> str:
    col = _color(status, error)
    icon = "✗" if error else "✓"
    detail = f'<div class="card-error">{_esc(error)}</div>' if error else ""
    return f"""
<div class="card">
  <div class="card-title">{_esc(title)}</div>
  <div class="card-status" style="color:{col}">{icon} {_esc(status)}</div>
  {detail}
</div>"""


def _esc(s: str | None) -> str:
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# Main HTML builder
# ---------------------------------------------------------------------------

def get_status_html() -> str:
    pg_status, pg_err = _check_postgres()
    redis_status, redis_err = _check_redis()
    celery_status, celery_err = _check_celery()
    prom_status, prom_err = _check_prometheus()

    log_lines = _recent_logs()
    last_backup = _last_backup()

    log_html = "\n".join(_esc(ln) for ln in log_lines) or "(empty)"

    services_html = (
        _service_card("PostgreSQL", pg_status, pg_err)
        + _service_card("Redis", redis_status, redis_err)
        + _service_card("Celery workers", celery_status, celery_err)
        + _service_card("Prometheus metrics", prom_status, prom_err)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Radar de Precios — Status</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0f1117;
      color: #c9d1d9;
      font-family: 'Courier New', Courier, monospace;
      font-size: 14px;
      line-height: 1.6;
      padding: 24px;
    }}
    a {{ color: #58a6ff; text-decoration: none; }}
    h1 {{ color: #e6edf3; font-size: 20px; margin-bottom: 4px; }}
    .subtitle {{ color: #8b949e; font-size: 12px; margin-bottom: 28px; }}
    .section {{ margin-bottom: 32px; }}
    .section-title {{
      color: #8b949e;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      border-bottom: 1px solid #21262d;
      padding-bottom: 6px;
      margin-bottom: 16px;
    }}
    .cards {{ display: flex; flex-wrap: wrap; gap: 12px; }}
    .card {{
      background: #161b22;
      border: 1px solid #21262d;
      border-radius: 6px;
      padding: 14px 18px;
      min-width: 200px;
      flex: 1 1 200px;
    }}
    .card-title {{ color: #8b949e; font-size: 11px; letter-spacing: 0.08em; margin-bottom: 6px; }}
    .card-status {{ font-size: 14px; font-weight: bold; }}
    .card-error {{ color: #ff4444; font-size: 11px; margin-top: 4px; word-break: break-all; }}
    .log-block {{
      background: #0d1117;
      border: 1px solid #21262d;
      border-radius: 6px;
      padding: 12px 16px;
      font-size: 12px;
      color: #8b949e;
      white-space: pre-wrap;
      word-break: break-all;
      max-height: 180px;
      overflow-y: auto;
    }}
    .backup-line {{ margin-top: 10px; color: #8b949e; font-size: 12px; }}
    .backup-line span {{ color: #ffaa00; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; }}
    .action-group {{ display: flex; flex-direction: column; gap: 6px; }}
    button {{
      background: #21262d;
      border: 1px solid #30363d;
      border-radius: 6px;
      color: #c9d1d9;
      cursor: pointer;
      font-family: inherit;
      font-size: 13px;
      padding: 8px 14px;
      transition: background 0.15s;
    }}
    button:hover {{ background: #30363d; }}
    .result-box {{
      background: #0d1117;
      border: 1px solid #21262d;
      border-radius: 6px;
      color: #8b949e;
      font-size: 12px;
      min-height: 32px;
      padding: 6px 10px;
      white-space: pre-wrap;
      word-break: break-all;
    }}
    .token-row {{
      display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
      font-size: 12px; color: #8b949e;
    }}
    .token-row input {{
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 4px;
      color: #c9d1d9;
      font-family: inherit;
      font-size: 12px;
      padding: 4px 8px;
      width: 340px;
    }}
    .refresh-note {{
      float: right;
      font-size: 11px;
      color: #8b949e;
      margin-top: -20px;
    }}
  </style>
</head>
<body>
  <h1>&#128225; Radar de Precios — Status</h1>
  <p class="subtitle">Auto-refreshes every 10 seconds &nbsp;|&nbsp; <a href="/">← App</a></p>

  <!-- SERVICES -->
  <div class="section">
    <div class="section-title">Services</div>
    <div class="cards">
      {services_html}
    </div>
  </div>

  <!-- RECENT ACTIVITY -->
  <div class="section">
    <div class="section-title">Recent Activity</div>
    <div class="log-block">{log_html}</div>
    <div class="backup-line">Last backup: <span>{_esc(last_backup)}</span></div>
  </div>

  <!-- QUICK ACTIONS -->
  <div class="section">
    <div class="section-title">Quick Actions</div>
    <div class="token-row">
      <label for="token">Admin Bearer token:</label>
      <input id="token" type="password" placeholder="paste JWT here for admin actions">
    </div>
    <div class="actions">
      <div class="action-group">
        <button onclick="doAction('POST', '/admin/test-alert', 'res-alert', true)">
          &#128276; Send test alert
        </button>
        <div id="res-alert" class="result-box">&nbsp;</div>
      </div>
      <div class="action-group">
        <button onclick="doAction('POST', '/admin/backup', 'res-backup', true)">
          &#128190; Trigger backup
        </button>
        <div id="res-backup" class="result-box">&nbsp;</div>
      </div>
      <div class="action-group">
        <button onclick="doAction('GET', '/monitoring/debug/celery-tasks', 'res-celery', false)">
          &#9658; Run Celery debug task
        </button>
        <div id="res-celery" class="result-box">&nbsp;</div>
      </div>
    </div>
  </div>

  <script>
    // Auto-refresh after 10 seconds
    setTimeout(() => location.reload(), 10000);

    async function doAction(method, path, resultId, needsAuth) {{
      const box = document.getElementById(resultId);
      box.style.color = '#8b949e';
      box.textContent = 'Sending…';
      const headers = {{'Content-Type': 'application/json'}};
      if (needsAuth) {{
        const tok = document.getElementById('token').value.trim();
        if (!tok) {{ box.style.color = '#ffaa00'; box.textContent = 'Paste an admin JWT token above first.'; return; }}
        headers['Authorization'] = 'Bearer ' + tok;
      }}
      try {{
        const resp = await fetch(path, {{method, headers}});
        const data = await resp.json().catch(() => ({{raw: await resp.text()}}));
        box.style.color = resp.ok ? '#00ff88' : '#ff4444';
        box.textContent = JSON.stringify(data, null, 2);
      }} catch (err) {{
        box.style.color = '#ff4444';
        box.textContent = 'Network error: ' + err.message;
      }}
    }}
  </script>
</body>
</html>"""
