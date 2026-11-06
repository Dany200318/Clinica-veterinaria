@echo off
REM =============================================================
REM  Respaldo de la base de datos MySQL (RNF-07, seccion 6.1.7)
REM  Genera respaldos\clinica_AAAA-MM-DD_HHMM.sql
REM  Programelo a diario en el Programador de tareas y copie la
REM  carpeta "respaldos" a un disco externo o a la nube.
REM =============================================================
setlocal
set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.4\bin
set DB=clinica_veterinaria
set USUARIO=clinica_app
REM La contrasena se pide al ejecutar. Para respaldos automaticos use un
REM archivo de opciones: mysql_config_editor set --login-path=respaldo --user=clinica_app --password
cd /d "%~dp0.."
if not exist respaldos mkdir respaldos
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set FECHA=%%i
"%MYSQL_BIN%\mysqldump.exe" -u %USUARIO% -p --single-transaction --routines --triggers --default-character-set=utf8mb4 %DB% > respaldos\clinica_%FECHA%.sql
if %ERRORLEVEL% EQU 0 (echo Respaldo creado: respaldos\clinica_%FECHA%.sql) else (echo ERROR al crear el respaldo)
REM Elimina respaldos con mas de 30 dias
forfiles /p respaldos /m *.sql /d -30 /c "cmd /c del @path" 2>nul
endlocal
