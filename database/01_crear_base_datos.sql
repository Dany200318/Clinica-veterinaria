-- =====================================================================
--  SISTEMA WEB DE GESTIÓN PARA UNA VETERINARIA
--  Script 01 — Creación de la base de datos y del usuario de la aplicación
--  Motor: MySQL 8.0.16 o superior (recomendado MySQL 8.4 LTS)
--  Ejecutar como root en MySQL Workbench (o: mysql -u root -p < 01_crear_base_datos.sql)
-- =====================================================================

-- 1. Base de datos con soporte completo de tildes, ñ y emojis (utf8mb4).
--    La intercalación utf8mb4_0900_ai_ci hace que las búsquedas ignoren
--    mayúsculas y tildes («gomez» encuentra «Gómez»).
CREATE DATABASE IF NOT EXISTS clinica_veterinaria
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

-- 2. Usuario exclusivo para la aplicación (principio de menor privilegio).
--    ¡Cambie la contraseña y use la misma en el archivo .env (DB_PASSWORD)!
CREATE USER IF NOT EXISTS 'clinica_app'@'localhost' IDENTIFIED BY 'Cl1n1c4_Vet_2026';

-- 3. Permisos sobre la base del sistema y sobre la base temporal de pruebas
--    que crea Django al ejecutar «python manage.py test».
GRANT ALL PRIVILEGES ON clinica_veterinaria.*      TO 'clinica_app'@'localhost';
GRANT ALL PRIVILEGES ON test_clinica_veterinaria.* TO 'clinica_app'@'localhost';
FLUSH PRIVILEGES;

-- Verificación
SHOW DATABASES LIKE 'clinica_veterinaria';
SELECT user, host FROM mysql.user WHERE user = 'clinica_app';
