@echo off
setlocal

echo.
echo MRA FOUNDATION 0.3 - BUILD 004
echo.

if not exist "docker-compose.yml" (
  echo ERRORE: esegui questo file dalla radice del repository mra-studio.
  pause
  exit /b 1
)

echo [1/5] Arresto container...
docker compose down
if errorlevel 1 goto :error

echo [2/5] Rimozione frontend duplicato nella radice...
if exist "src" rmdir /s /q "src"

echo [3/5] Pulizia volume dipendenze frontend...
docker volume rm mra-studio_studio_node_modules >nul 2>&1

echo [4/5] Ricostruzione senza cache...
docker compose build --no-cache
if errorlevel 1 goto :error

echo [5/5] Avvio MRA Studio...
docker compose up
exit /b 0

:error
echo.
echo OPERAZIONE INTERROTTA. Copia qui l'errore mostrato sopra.
pause
exit /b 1
