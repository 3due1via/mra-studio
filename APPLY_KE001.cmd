@echo off
setlocal

if not exist "docker-compose.yml" (
  echo ERRORE: esegui questo file dalla radice del repository.
  pause
  exit /b 1
)

echo Arresto dei container...
docker compose down
if errorlevel 1 goto :error

echo Ricostruzione API...
docker compose build --no-cache api
if errorlevel 1 goto :error

echo Avvio dell'ambiente...
docker compose up
exit /b 0

:error
echo.
echo Operazione interrotta. Copia l'errore mostrato sopra.
pause
exit /b 1
