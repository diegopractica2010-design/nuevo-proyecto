@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo ============================================================
echo    Radar de Precios - Inicio local (sin Docker)
echo ============================================================
echo.
echo  1) Espera a que aparezca el texto "Uvicorn running".
echo  2) Abre tu navegador en:   http://localhost:8001
echo  3) Para DETENER la app:    cierra esta ventana.
echo.
echo ============================================================
echo.
REM Abre el navegador solo, tras dar unos segundos a que arranque el servidor
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8001"
"%~dp0venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
pause
