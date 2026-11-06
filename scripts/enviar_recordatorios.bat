@echo off
REM =============================================================
REM  Tarea programada de recordatorios (RF-16)
REM  Programela en el "Programador de tareas" de Windows para que
REM  se ejecute todos los dias (por ejemplo a las 07:00).
REM =============================================================
cd /d "%~dp0.."
call venv\Scripts\activate
if not exist logs mkdir logs
python manage.py enviar_recordatorios >> logs\recordatorios.log 2>&1
