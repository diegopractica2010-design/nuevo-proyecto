@echo off
setlocal

echo ============================================================
echo   Radar de Precios - Iniciar con Docker
echo ============================================================
echo.

REM Verificar que Docker este corriendo
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker no esta corriendo.
    echo Abre Docker Desktop y espera a que inicie, luego vuelve a ejecutar este script.
    pause
    exit /b 1
)

echo Docker detectado. Iniciando servicios...
echo.
echo Primera vez: la construccion puede tardar 5-10 minutos (descarga imagenes + compila frontend).
echo Las proximas veces sera mucho mas rapido.
echo.

REM Construir y arrancar todos los servicios
docker-compose -f docker-compose.standalone.yml up --build -d

if errorlevel 1 (
    echo.
    echo ERROR: Fallo al iniciar los servicios.
    echo Revisa los logs con: docker-compose -f docker-compose.standalone.yml logs
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Servicios iniciados correctamente!
echo.
echo   Aplicacion:  http://localhost
echo   API directa: http://localhost:8001
echo   API docs:    http://localhost:8001/docs
echo.
echo   Para ver logs:    docker-compose -f docker-compose.standalone.yml logs -f
echo   Para detener:     stop.bat
echo ============================================================
echo.

pause
