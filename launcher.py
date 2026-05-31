"""
Entry point for PyInstaller executable.
Run this file to start the Radar de Precios server.
"""
import multiprocessing
import sys
import os


def main():
    # When frozen as .exe, ensure the data directory exists next to the exe
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(exe_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'backups'), exist_ok=True)

    import uvicorn
    from backend.main import app

    print("\n" + "=" * 60)
    print("  Radar de Precios")
    print("  Servidor en:  http://localhost:8001")
    print("  Presiona Ctrl+C para detener")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False, workers=1)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
