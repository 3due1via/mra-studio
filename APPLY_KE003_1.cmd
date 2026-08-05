@echo off
setlocal

if not exist "docker-compose.yml" (
  echo ERRORE: copia questo file nella radice del repository mra-studio.
  pause
  exit /b 1
)

echo Arresto dei container...
docker compose down
if errorlevel 1 goto :error

echo Ricostruzione del frontend...
docker compose build --no-cache studio
if errorlevel 1 goto :error

echo Avvio di MRA Studio...
docker compose up
exit /b 0

:error
echo.
echo Operazione interrotta. Copia l'errore mostrato sopra.
pause
exit /b 1
