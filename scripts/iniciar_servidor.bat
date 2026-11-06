@echo off
REM =============================================================
REM  Inicia el sistema en la red local de la clinica (puerto 8000)
REM  Los demas equipos ingresan con:  http://IP-DEL-SERVIDOR:8000
REM =============================================================
cd /d "%~dp0.."
call venv\Scripts\activate
python manage.py collectstatic --noinput >nul
echo Sistema disponible en http://localhost:8000  (Ctrl+C para detener)
waitress-serve --listen=0.0.0.0:8000 clinica.wsgi:application
