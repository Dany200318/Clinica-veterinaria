@echo off
REM =============================================================
REM  Restaura un respaldo:  restaurar_bd.bat respaldos\clinica_2026-11-06_0700.sql
REM =============================================================
setlocal
set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.4\bin
if "%~1"=="" (echo Uso: restaurar_bd.bat ruta\del\respaldo.sql & exit /b 1)
echo ATENCION: se reemplazaran los datos actuales de clinica_veterinaria.
pause
"%MYSQL_BIN%\mysql.exe" -u root -p --default-character-set=utf8mb4 clinica_veterinaria < "%~1"
if %ERRORLEVEL% EQU 0 (echo Restauracion completada.) else (echo ERROR en la restauracion)
endlocal
