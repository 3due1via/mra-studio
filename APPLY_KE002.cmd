@echo off
setlocal
if not exist "docker-compose.yml" (
  echo ERRORE: copia questo file nella radice del repository mra-studio.
  pause
  exit /b 1
)
echo Riavvio del frontend MRA Studio...
docker compose restart studio
if errorlevel 1 goto :error
echo.
echo KE-002 applicato. Apri http://localhost:5173/knowledge
pause
exit /b 0
:error
echo Errore durante il riavvio. Copia qui il messaggio mostrato.
pause
exit /b 1
