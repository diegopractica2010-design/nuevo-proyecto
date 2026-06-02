"""
Entry point for PyInstaller executable.
Starts the uvicorn API server and opens the browser automatically.

Note: Celery worker/beat cannot run inside a frozen exe because sys.executable
is the exe itself (not a Python interpreter). Use docker-compose.standalone.yml
(start.bat) for full Celery support with background tasks.
"""
import multiprocessing
import sys
import os
import threading
import time
import webbrowser

URL = "http://localhost:8001"


def _open_browser() -> None:
    """Wait for the server to be ready, then open the browser."""
    time.sleep(3)
    try:
        import urllib.request
        for _ in range(15):
            try:
                urllib.request.urlopen(URL, timeout=1)
                break
            except Exception:
                time.sleep(1)
    except Exception:
        pass
    webbrowser.open(URL)


def main() -> None:
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(exe_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'backups'), exist_ok=True)

    import uvicorn
    from backend.main import app

    print("\n" + "=" * 60)
    print("  Radar de Precios")
    print("  Servidor en:  " + URL)
    print("  Abriendo navegador automaticamente...")
    print("  Presiona Ctrl+C para detener")
    print("=" * 60 + "\n")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False, workers=1)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
