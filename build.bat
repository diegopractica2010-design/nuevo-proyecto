@echo off
echo ============================================================
echo   Radar de Precios - Compilar ejecutable
echo ============================================================
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
) else (
    echo AVISO: No se encontro entorno virtual, usando Python del sistema.
)

REM Instalar PyInstaller si no esta instalado
echo Verificando PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

REM Limpiar builds anteriores
if exist "dist\RadarPrecios" (
    echo Limpiando build anterior...
    rmdir /s /q "dist\RadarPrecios"
)
if exist "build\RadarPrecios" (
    rmdir /s /q "build\RadarPrecios"
)

REM Compilar
echo.
echo Compilando... (esto puede tardar 2-5 minutos)
echo.
pyinstaller radar_precios.spec

REM Verificar resultado
if exist "dist\RadarPrecios\RadarPrecios.exe" (
    echo.
    echo ============================================================
    echo   Compilacion exitosa!
    echo.
    echo   Ejecutable: dist\RadarPrecios\RadarPrecios.exe
    echo.
    echo   Para distribuir: copia toda la carpeta dist\RadarPrecios\
    echo   (el .exe necesita los archivos que estan junto a el)
    echo ============================================================
) else (
    echo.
    echo ERROR: La compilacion fallo. Revisa los mensajes de arriba.
    exit /b 1
)

pause
