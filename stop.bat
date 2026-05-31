@echo off
echo Deteniendo Radar de Precios...
docker-compose -f docker-compose.standalone.yml down
echo.
echo Servicios detenidos. Los datos (base de datos, cache) se conservan.
echo Para eliminar tambien los datos: docker-compose -f docker-compose.standalone.yml down -v
echo.
pause
