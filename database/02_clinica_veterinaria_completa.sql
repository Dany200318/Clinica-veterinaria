-- =====================================================================
--  SISTEMA WEB DE GESTIÓN PARA UNA VETERINARIA
--  Script 02 — BASE DE DATOS COMPLETA Y FUNCIONAL (estructura + datos)
--
--  Contiene:
--    1. Tablas internas de Django (usuarios, grupos/roles, permisos,
--       sesiones, bitácora del admin y control de migraciones).
--    2. Tablas del negocio según el diccionario de datos (Tablas 5.1–5.5):
--       propietario, paciente, veterinario, cita + vacuna, notificacion
--       y configuracion_correo.
--    3. Roles (Administrador, Veterinario, Recepcionista) y usuarios iniciales.
--    4. Datos de prueba (fechas relativas a HOY).
--    5. Vistas, procedimientos almacenados y triggers (regla anti-traslape).
--
--  Uso (MySQL Workbench: File > Open SQL Script > Ejecutar ⚡):
--    mysql -u root -p < 02_clinica_veterinaria_completa.sql
--  Después ejecute en el proyecto:  python manage.py migrate
--    (responderá «No migrations to apply» y creará los permisos de Django).
--
--  ⚠ ADVERTENCIA: este script BORRA y vuelve a crear las tablas. No lo
--    ejecute sobre una base con información real; use un respaldo.
--
--  Usuarios creados (cambie las contraseñas al primer ingreso):
--    admin        / Admin2026!     (Administrador, superusuario)
--    veterinaria  / Clinica2026!   (Veterinario)
--    recepcion    / Clinica2026!   (Recepcionista)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS clinica_veterinaria
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE clinica_veterinaria;

SET NAMES utf8mb4;
SET time_zone = '+00:00';          -- Django guarda las fechas-hora en UTC (USE_TZ = True)
SET FOREIGN_KEY_CHECKS = 0;

DROP TRIGGER  IF EXISTS trg_cita_validar_insert;
DROP TRIGGER  IF EXISTS trg_cita_validar_update;
DROP PROCEDURE IF EXISTS sp_verificar_disponibilidad;
DROP PROCEDURE IF EXISTS sp_reporte_citas_periodo;
DROP PROCEDURE IF EXISTS sp_agenda_veterinario;
DROP VIEW IF EXISTS v_citas_detalle, v_agenda_hoy, v_resumen_mensual_citas,
                    v_vacunas_por_vencer, v_indicadores_panel, v_efectividad_notificaciones;

DROP TABLE IF EXISTS notificacion, configuracion_correo, cita, veterinario, vacuna, paciente, propietario,
                     django_admin_log, django_session, auth_user_user_permissions, auth_user_groups,
                     auth_group_permissions, auth_permission, auth_group, auth_user,
                     django_content_type, django_migrations;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- 1. TABLAS INTERNAS DE DJANGO 5.2 (idénticas a las que crea «migrate»)
-- =====================================================================
CREATE TABLE django_migrations (
    id       BIGINT       NOT NULL AUTO_INCREMENT,
    app      VARCHAR(255) NOT NULL,
    name     VARCHAR(255) NOT NULL,
    applied  DATETIME(6)  NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE django_content_type (
    id        INT          NOT NULL AUTO_INCREMENT,
    app_label VARCHAR(100) NOT NULL,
    model     VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY django_content_type_app_label_model_76bd3d3b_uniq (app_label, model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE auth_permission (
    id              INT          NOT NULL AUTO_INCREMENT,
    name            VARCHAR(255) NOT NULL,
    content_type_id INT          NOT NULL,
    codename        VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY auth_permission_content_type_id_codename_01ab375a_uniq (content_type_id, codename),
    CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co
        FOREIGN KEY (content_type_id) REFERENCES django_content_type (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabla 5.1 (nota): los roles se guardan como grupos
CREATE TABLE auth_group (
    id   INT          NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE auth_group_permissions (
    id            BIGINT NOT NULL AUTO_INCREMENT,
    group_id      INT    NOT NULL,
    permission_id INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY auth_group_permissions_group_id_permission_id_0cd325b0_uniq (group_id, permission_id),
    CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id
        FOREIGN KEY (group_id) REFERENCES auth_group (id),
    CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm
        FOREIGN KEY (permission_id) REFERENCES auth_permission (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabla 5.1 — Entidad USUARIO
CREATE TABLE auth_user (
    id           INT          NOT NULL AUTO_INCREMENT,
    password     VARCHAR(128) NOT NULL COMMENT 'Hash PBKDF2-SHA256 de Django (RF-04)',
    last_login   DATETIME(6)  NULL,
    is_superuser TINYINT(1)   NOT NULL,
    username     VARCHAR(150) NOT NULL,
    first_name   VARCHAR(150) NOT NULL,
    last_name    VARCHAR(150) NOT NULL,
    email        VARCHAR(254) NOT NULL,
    is_staff     TINYINT(1)   NOT NULL,
    is_active    TINYINT(1)   NOT NULL,
    date_joined  DATETIME(6)  NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE auth_user_groups (
    id       BIGINT NOT NULL AUTO_INCREMENT,
    user_id  INT    NOT NULL,
    group_id INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY auth_user_groups_user_id_group_id_94350c0c_uniq (user_id, group_id),
    CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user (id),
    CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES auth_group (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE auth_user_user_permissions (
    id            BIGINT NOT NULL AUTO_INCREMENT,
    user_id       INT    NOT NULL,
    permission_id INT    NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY auth_user_user_permissions_user_id_permission_id_14a6b632_uniq (user_id, permission_id),
    CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id
        FOREIGN KEY (user_id) REFERENCES auth_user (id),
    CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm
        FOREIGN KEY (permission_id) REFERENCES auth_permission (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE django_admin_log (
    id              INT               NOT NULL AUTO_INCREMENT,
    action_time     DATETIME(6)       NOT NULL,
    object_id       LONGTEXT          NULL,
    object_repr     VARCHAR(200)      NOT NULL,
    action_flag     SMALLINT UNSIGNED NOT NULL,
    change_message  LONGTEXT          NOT NULL,
    content_type_id INT               NULL,
    user_id         INT               NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT django_admin_log_chk_1 CHECK (action_flag >= 0),
    CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co
        FOREIGN KEY (content_type_id) REFERENCES django_content_type (id),
    CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id
        FOREIGN KEY (user_id) REFERENCES auth_user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE django_session (
    session_key  VARCHAR(40) NOT NULL,
    session_data LONGTEXT    NOT NULL,
    expire_date  DATETIME(6) NOT NULL,
    PRIMARY KEY (session_key),
    KEY django_session_expire_date_a5c62663 (expire_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- =====================================================================
-- 2. TABLAS DEL NEGOCIO (diccionario de datos, Capítulo V)
-- =====================================================================

-- Tabla 5.2 — Entidad PROPIETARIO
CREATE TABLE propietario (
    id_propietario INT          NOT NULL AUTO_INCREMENT COMMENT 'Identificador del propietario',
    nombre         VARCHAR(150) NOT NULL COMMENT 'Nombre completo',
    telefono       VARCHAR(20)  NOT NULL COMMENT 'Teléfono de contacto',
    email          VARCHAR(254) NOT NULL COMMENT 'Destino de los correos de notificación',
    direccion      VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'Dirección de residencia',
    dpi            VARCHAR(13)  NULL     COMMENT 'Documento Personal de Identificación (13 dígitos)',
    zona           VARCHAR(50)  NOT NULL DEFAULT '' COMMENT 'Zona o ubicación del domicilio',
    PRIMARY KEY (id_propietario),
    UNIQUE KEY uq_propietario_dpi (dpi),
    KEY idx_propietario_nombre (nombre),
    KEY idx_propietario_email (email),
    CONSTRAINT chk_propietario_dpi CHECK (dpi IS NULL OR dpi REGEXP '^[0-9]{13}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Tabla 5.2 - Propietarios de las mascotas';

-- Tabla 5.3 — Entidad PACIENTE
CREATE TABLE paciente (
    id_paciente      INT           NOT NULL AUTO_INCREMENT COMMENT 'Identificador del paciente',
    nombre           VARCHAR(100)  NOT NULL COMMENT 'Nombre de la mascota',
    especie          VARCHAR(20)   NOT NULL COMMENT 'Perro, Gato u Otro',
    raza             VARCHAR(100)  NOT NULL,
    sexo             VARCHAR(1)    NOT NULL COMMENT 'M = Macho, H = Hembra',
    color            VARCHAR(50)   NOT NULL DEFAULT '' COMMENT 'Color del pelaje',
    fecha_nacimiento DATE          NULL     COMMENT 'Permite calcular la edad',
    peso             DECIMAL(6,2)  NULL     COMMENT 'Peso actual en libras (lb)',
    microchip        VARCHAR(30)   NOT NULL DEFAULT '' COMMENT 'Número de microchip, si lo tiene',
    esterilizado     TINYINT(1)    NOT NULL DEFAULT 0,
    alergias         LONGTEXT      NOT NULL COMMENT 'Alergias conocidas, resaltadas en la ficha',
    observaciones    LONGTEXT      NOT NULL,
    fecha_registro   DATE          NOT NULL COMMENT 'Fecha de alta en el sistema',
    id_propietario   INT           NOT NULL COMMENT 'FK -> propietario',
    PRIMARY KEY (id_paciente),
    KEY idx_paciente_nombre (nombre),
    KEY idx_paciente_propietario (id_propietario),
    KEY idx_paciente_especie (especie),
    CONSTRAINT fk_paciente_propietario FOREIGN KEY (id_propietario)
        REFERENCES propietario (id_propietario) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_paciente_sexo CHECK (sexo IN ('M', 'H')),
    CONSTRAINT chk_paciente_especie CHECK (especie IN ('Perro', 'Gato', 'Otro')),
    CONSTRAINT chk_paciente_peso CHECK (peso IS NULL OR peso >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Tabla 5.3 - Pacientes (mascotas)';

-- Control de vacunas (objetivo específico 4, Tabla 6.5)
CREATE TABLE vacuna (
    id_vacuna        INT          NOT NULL AUTO_INCREMENT,
    nombre           VARCHAR(100) NOT NULL COMMENT 'Nombre de la vacuna o tratamiento preventivo',
    fecha_aplicacion DATE         NOT NULL,
    fecha_proxima    DATE         NULL     COMMENT 'Próxima dosis: genera recordatorio por correo',
    lote             VARCHAR(50)  NOT NULL DEFAULT '',
    observaciones    LONGTEXT     NOT NULL,
    id_paciente      INT          NOT NULL COMMENT 'FK -> paciente',
    PRIMARY KEY (id_vacuna),
    KEY idx_vacuna_fecha_proxima (fecha_proxima),
    KEY idx_vacuna_paciente (id_paciente),
    CONSTRAINT fk_vacuna_paciente FOREIGN KEY (id_paciente)
        REFERENCES paciente (id_paciente) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_vacuna_fechas CHECK (fecha_proxima IS NULL OR fecha_proxima > fecha_aplicacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Vacunas aplicadas y próximas dosis';

-- Tabla 5.4 — Entidad VETERINARIO
CREATE TABLE veterinario (
    id_veterinario  INT          NOT NULL AUTO_INCREMENT,
    nombre_completo VARCHAR(150) NOT NULL COMMENT 'Nombre con el que aparece en citas y reportes',
    activo          TINYINT(1)   NOT NULL DEFAULT 1 COMMENT 'Veterinario en servicio',
    id_usuario      INT          NULL     COMMENT 'FK opcional -> auth_user (para «mis citas»)',
    PRIMARY KEY (id_veterinario),
    UNIQUE KEY uq_veterinario_usuario (id_usuario),
    CONSTRAINT fk_veterinario_usuario FOREIGN KEY (id_usuario)
        REFERENCES auth_user (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Tabla 5.4 - Veterinarios';

-- Tabla 5.5 — Entidad CITA
CREATE TABLE cita (
    id_cita             INT          NOT NULL AUTO_INCREMENT,
    fecha_cita          DATE         NOT NULL,
    hora_inicio         TIME(6)      NOT NULL,
    hora_fin            TIME(6)      NULL     COMMENT 'Si es NULL se asume una duración de 30 minutos',
    motivo              LONGTEXT     NOT NULL COMMENT 'Motivo de la consulta',
    tipo_cita           VARCHAR(20)  NOT NULL DEFAULT '' COMMENT 'consulta, vacunacion, desparasitacion, cirugia, control, emergencia',
    estado              VARCHAR(15)  NOT NULL DEFAULT 'pendiente' COMMENT 'pendiente, confirmada, completada, cancelada',
    notas               LONGTEXT     NOT NULL,
    fecha_creacion      DATETIME(6)  NOT NULL COMMENT 'UTC',
    fecha_actualizacion DATETIME(6)  NOT NULL COMMENT 'UTC',
    id_usuario_registro INT          NULL     COMMENT 'FK -> auth_user que registró la cita',
    id_paciente         INT          NOT NULL COMMENT 'FK -> paciente',
    id_veterinario      INT          NOT NULL COMMENT 'FK -> veterinario',
    PRIMARY KEY (id_cita),
    KEY idx_cita_vet_fecha (id_veterinario, fecha_cita),
    KEY idx_cita_fecha_estado (fecha_cita, estado),
    KEY idx_cita_paciente (id_paciente),
    KEY idx_cita_usuario (id_usuario_registro),
    CONSTRAINT fk_cita_paciente FOREIGN KEY (id_paciente)
        REFERENCES paciente (id_paciente) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_cita_veterinario FOREIGN KEY (id_veterinario)
        REFERENCES veterinario (id_veterinario) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_cita_usuario FOREIGN KEY (id_usuario_registro)
        REFERENCES auth_user (id) ON DELETE SET NULL,
    CONSTRAINT chk_cita_hora_fin_mayor CHECK (hora_fin IS NULL OR hora_fin > hora_inicio),
    CONSTRAINT chk_cita_estado CHECK (estado IN ('pendiente', 'confirmada', 'completada', 'cancelada'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Tabla 5.5 - Citas médicas';

-- Configuración SMTP editable desde el sistema (RF-17). Registro único id = 1.
CREATE TABLE configuracion_correo (
    id                       BIGINT            NOT NULL AUTO_INCREMENT,
    usar_esta_configuracion  TINYINT(1)        NOT NULL DEFAULT 0,
    servidor                 VARCHAR(150)      NOT NULL DEFAULT 'smtp.gmail.com',
    puerto                   INT UNSIGNED      NOT NULL DEFAULT 587,
    usar_tls                 TINYINT(1)        NOT NULL DEFAULT 1,
    usar_ssl                 TINYINT(1)        NOT NULL DEFAULT 0,
    usuario                  VARCHAR(150)      NOT NULL DEFAULT '',
    contrasena               VARCHAR(150)      NOT NULL DEFAULT '',
    remitente                VARCHAR(150)      NOT NULL DEFAULT '',
    dias_recordatorio_cita   SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    dias_recordatorio_vacuna SMALLINT UNSIGNED NOT NULL DEFAULT 7,
    fecha_actualizacion      DATETIME(6)       NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Parámetros del servidor de correo (RF-17)';

-- Bitácora de correos (RF-15). Fuente del indicador «notificaciones entregadas».
CREATE TABLE notificacion (
    id_notificacion INT          NOT NULL AUTO_INCREMENT,
    tipo            VARCHAR(25)  NOT NULL COMMENT 'confirmacion, modificacion, cancelacion, recordatorio_cita, recordatorio_vacuna, prueba',
    destinatario    VARCHAR(254) NOT NULL,
    asunto          VARCHAR(200) NOT NULL,
    estado          VARCHAR(10)  NOT NULL COMMENT 'enviado o error',
    detalle_error   LONGTEXT     NOT NULL,
    fecha_envio     DATETIME(6)  NOT NULL COMMENT 'UTC',
    id_cita         INT          NULL,
    id_vacuna       INT          NULL,
    PRIMARY KEY (id_notificacion),
    KEY idx_notif_tipo_estado (tipo, estado),
    KEY idx_notif_fecha (fecha_envio),
    KEY idx_notif_cita (id_cita),
    KEY idx_notif_vacuna (id_vacuna),
    CONSTRAINT fk_notif_cita FOREIGN KEY (id_cita) REFERENCES cita (id_cita) ON DELETE SET NULL,
    CONSTRAINT fk_notif_vacuna FOREIGN KEY (id_vacuna) REFERENCES vacuna (id_vacuna) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Historial de notificaciones por correo';

-- =====================================================================
-- 3. CONTROL DE MIGRACIONES
--    Registra como aplicadas las migraciones de Django y del sistema, para
--    que «python manage.py migrate» no intente crear de nuevo las tablas.
-- =====================================================================
INSERT INTO django_migrations (app, name, applied) VALUES
    ('contenttypes', '0001_initial', UTC_TIMESTAMP(6)),
    ('auth', '0001_initial', UTC_TIMESTAMP(6)),
    ('admin', '0001_initial', UTC_TIMESTAMP(6)),
    ('admin', '0002_logentry_remove_auto_add', UTC_TIMESTAMP(6)),
    ('admin', '0003_logentry_add_action_flag_choices', UTC_TIMESTAMP(6)),
    ('contenttypes', '0002_remove_content_type_name', UTC_TIMESTAMP(6)),
    ('auth', '0002_alter_permission_name_max_length', UTC_TIMESTAMP(6)),
    ('auth', '0003_alter_user_email_max_length', UTC_TIMESTAMP(6)),
    ('auth', '0004_alter_user_username_opts', UTC_TIMESTAMP(6)),
    ('auth', '0005_alter_user_last_login_null', UTC_TIMESTAMP(6)),
    ('auth', '0006_require_contenttypes_0002', UTC_TIMESTAMP(6)),
    ('auth', '0007_alter_validators_add_error_messages', UTC_TIMESTAMP(6)),
    ('auth', '0008_alter_user_username_max_length', UTC_TIMESTAMP(6)),
    ('auth', '0009_alter_user_last_name_max_length', UTC_TIMESTAMP(6)),
    ('auth', '0010_alter_group_name_max_length', UTC_TIMESTAMP(6)),
    ('auth', '0011_update_proxy_permissions', UTC_TIMESTAMP(6)),
    ('auth', '0012_alter_user_first_name_max_length', UTC_TIMESTAMP(6)),
    ('pacientes', '0001_initial', UTC_TIMESTAMP(6)),
    ('citas', '0001_initial', UTC_TIMESTAMP(6)),
    ('notificaciones', '0001_initial', UTC_TIMESTAMP(6)),
    ('sessions', '0001_initial', UTC_TIMESTAMP(6)),
    ('usuarios', '0001_crear_roles', UTC_TIMESTAMP(6));


-- =====================================================================
-- 4. ROLES Y USUARIOS INICIALES (RF-01 a RF-04)
--    Contraseñas cifradas con PBKDF2-SHA256 (1 000 000 iteraciones).
-- =====================================================================
INSERT INTO auth_group (id, name) VALUES
    (1, 'Administrador'),
    (2, 'Veterinario'),
    (3, 'Recepcionista');

INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name,
                       email, is_staff, is_active, date_joined) VALUES
    (1, 'pbkdf2_sha256$1000000$mRz7ahctiYcExEpR549CBB$d4dl+9mheM8vs93C+wtMf7YKOX5AsGHr0YACgdQ/c9U=',
        NULL, 1, 'admin', 'Administrador', 'del Sistema', 'admin@clinica.local', 1, 1, UTC_TIMESTAMP(6)),
    (2, 'pbkdf2_sha256$1000000$OOiJChDBp2LNxp1ePKIlOP$p0fZzxDskjyWOcVONEKODo7q2UCi/Tk4q298kYhD74I=',
        NULL, 0, 'veterinaria', 'Ana Lucía', 'Morales', 'veterinaria@clinica.local', 0, 1, UTC_TIMESTAMP(6)),
    (3, 'pbkdf2_sha256$1000000$OOiJChDBp2LNxp1ePKIlOP$p0fZzxDskjyWOcVONEKODo7q2UCi/Tk4q298kYhD74I=',
        NULL, 0, 'recepcion', 'Karla', 'Méndez', 'recepcion@clinica.local', 0, 1, UTC_TIMESTAMP(6));

INSERT INTO auth_user_groups (user_id, group_id) VALUES
    (1, 1),   -- admin       -> Administrador
    (2, 2),   -- veterinaria -> Veterinario
    (3, 3);   -- recepcion   -> Recepcionista


-- =====================================================================
-- 5. DATOS DE PRUEBA (las fechas se calculan desde HOY)
-- =====================================================================
INSERT INTO configuracion_correo (id, usar_esta_configuracion, servidor, puerto, usar_tls, usar_ssl,
                                  usuario, contrasena, remitente, dias_recordatorio_cita,
                                  dias_recordatorio_vacuna, fecha_actualizacion)
VALUES (1, 0, 'smtp.gmail.com', 587, 1, 0, '', '', '', 1, 7, UTC_TIMESTAMP(6));

INSERT INTO veterinario (id_veterinario, nombre_completo, activo, id_usuario) VALUES
    (1, 'Dra. Ana Lucía Morales', 1, 2),
    (2, 'Dr. Luis Fernando Ortiz', 1, NULL),
    (3, 'Dra. Estefanía López Calderón', 0, NULL);

INSERT INTO propietario (id_propietario, nombre, telefono, email, direccion, dpi, zona) VALUES
    (1, 'María Fernanda López García',   '5512-3456', 'maria.lopez@ejemplo.com',    'Barrio El Calvario, 3a. calle 4-15', '1234567890101', 'Zona 1, Amatitlán'),
    (2, 'José Antonio Pérez Ramírez',    '4423-7788', 'jose.perez@ejemplo.com',     'Colonia San Antonio, lote 12',       '2345678901201', 'Zona 2, Amatitlán'),
    (3, 'Ana Lucía Hernández Ruiz',      '3301-2299', 'ana.hernandez@ejemplo.com',  '5a. avenida 2-30',                   '3456789012301', 'Villa Canales'),
    (4, 'Carlos Eduardo Gómez Díaz',     '5590-1122', 'carlos.gomez@ejemplo.com',   'Residenciales Las Flores, casa 8',   NULL,            'Zona 4, Amatitlán'),
    (5, 'Sofía Alejandra Castillo Mejía','4788-6655', 'sofia.castillo@ejemplo.com', 'Calle principal 10-20',              '4567890123401', 'Palín, Escuintla');

INSERT INTO paciente (id_paciente, nombre, especie, raza, sexo, color, fecha_nacimiento, peso, microchip,
                      esterilizado, alergias, observaciones, fecha_registro, id_propietario) VALUES
    (1, 'Max',    'Perro', 'Labrador Retriever',      'M', 'Dorado',        CURDATE() - INTERVAL 4 YEAR, 62.83, '985112003456781', 1, '',                           'Paciente muy dócil.',             CURDATE() - INTERVAL 160 DAY, 1),
    (2, 'Luna',   'Gato',  'Siamés',                  'H', 'Crema',         CURDATE() - INTERVAL 2 YEAR,  9.26, '',                1, 'Penicilina',                 '',                                CURDATE() - INTERVAL 150 DAY, 1),
    (3, 'Rocky',  'Perro', 'Pastor Alemán',           'M', 'Negro y fuego', CURDATE() - INTERVAL 6 YEAR, 74.96, '985112003456782', 0, '',                           'Displasia de cadera leve.',       CURDATE() - INTERVAL 155 DAY, 2),
    (4, 'Mía',    'Gato',  'Doméstico de pelo corto', 'H', 'Atigrado',      CURDATE() - INTERVAL 1 YEAR,  6.83, '',                0, '',                           '',                                CURDATE() - INTERVAL 50 DAY,  3),
    (5, 'Toby',   'Perro', 'Beagle',                  'M', 'Tricolor',      CURDATE() - INTERVAL 3 YEAR, 28.22, '',                1, 'Pollo (alergia alimentaria)', 'Dieta hipoalergénica.',          CURDATE() - INTERVAL 75 DAY,  3),
    (6, 'Canela', 'Perro', 'Mestizo',                 'H', 'Café',          CURDATE() - INTERVAL 5 YEAR, 33.73, '',                1, '',                           '',                                CURDATE() - INTERVAL 65 DAY,  4),
    (7, 'Simba',  'Gato',  'Persa',                   'M', 'Naranja',       CURDATE() - INTERVAL 7 YEAR,  12.35, '985112003456783', 1, 'Sulfas',                     'Propenso a bolas de pelo.',       CURDATE() - INTERVAL 10 DAY,  5);

-- Citas: pasadas (historial), de hoy y próximas. Ninguna se traslapa por veterinario.
INSERT INTO cita (fecha_cita, hora_inicio, hora_fin, motivo, tipo_cita, estado, notas,
                  fecha_creacion, fecha_actualizacion, id_usuario_registro, id_paciente, id_veterinario) VALUES
    (CURDATE() - INTERVAL 150 DAY, '09:00', '09:30', 'Control de cadera',             'control',         'completada', 'Se indicó condroprotector.', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 3, 1),
    (CURDATE() - INTERVAL 120 DAY, '10:00', '10:30', 'Vacuna antirrábica anual',      'vacunacion',      'completada', '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 1, 1),
    (CURDATE() - INTERVAL 95 DAY,  '11:00', '11:30', 'Revisión general',              'consulta',        'completada', 'Sin hallazgos.',              UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 2, 2),
    (CURDATE() - INTERVAL 70 DAY,  '15:00', '15:30', 'Desparasitación interna',       'desparasitacion', 'completada', '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 5, 2),
    (CURDATE() - INTERVAL 60 DAY,  '08:30', '09:30', 'Esterilización',                'cirugia',         'completada', 'Recuperación sin complicaciones.', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 6, 1),
    (CURDATE() - INTERVAL 45 DAY,  '14:00', '14:30', 'Primera vacuna triple felina',  'vacunacion',      'completada', '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 4, 2),
    (CURDATE() - INTERVAL 30 DAY,  '16:00', '16:30', 'Dermatitis',                    'consulta',        'cancelada',  'El propietario canceló.',     UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 7, 1),
    (CURDATE() - INTERVAL 20 DAY,  '09:00', '09:30', 'Vómitos frecuentes',            'consulta',        'completada', 'Gastritis leve; dieta blanda.', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 3, 2),
    (CURDATE() - INTERVAL 7 DAY,   '10:00', '10:30', 'Cojera pata trasera',           'consulta',        'completada', 'Reposo 10 días.',             UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 1, 1),
    (CURDATE() - INTERVAL 3 DAY,   '11:00', '11:30', 'Control de alergia alimentaria','control',         'pendiente',  '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 5, 1),
    (CURDATE(),                    '09:00', '09:30', 'Control post vacuna',           'control',         'confirmada', '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 2, 1),
    (CURDATE(),                    '10:00', '10:45', 'Limpieza dental',               'consulta',        'pendiente',  '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 3, 2),
    (CURDATE(),                    '15:00', '15:30', 'Refuerzo triple felina',        'vacunacion',      'completada', '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 4, 1),
    (CURDATE() + INTERVAL 1 DAY,   '08:30', '09:00', 'Retiro de puntos',              'control',         'confirmada', '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 6, 2),
    (CURDATE() + INTERVAL 2 DAY,   '11:00', '11:30', 'Revisión de piel',              'consulta',        'pendiente',  'Paciente alérgico a sulfas.', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 7, 1),
    (CURDATE() + INTERVAL 4 DAY,   '14:00', '14:30', 'Desparasitación',               'desparasitacion', 'pendiente',  '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 1, 2),
    (CURDATE() + INTERVAL 6 DAY,   '16:00', '16:30', 'Vacuna antirrábica',            'vacunacion',      'pendiente',  '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 5, 1),
    (CURDATE() + INTERVAL 12 DAY,  '09:30', '10:00', 'Chequeo general',               'consulta',        'pendiente',  '',                            UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 3, 2, 2);

INSERT INTO vacuna (nombre, fecha_aplicacion, fecha_proxima, lote, observaciones, id_paciente) VALUES
    ('Rabia',                             CURDATE() - INTERVAL 120 DAY, CURDATE() + INTERVAL 245 DAY, 'RB-2026-114', '', 1),
    ('Parvovirus + Moquillo (Quíntuple)', CURDATE() - INTERVAL 200 DAY, CURDATE() + INTERVAL 5 DAY,   'QT-0091',     '', 1),
    ('Triple felina',                     CURDATE() - INTERVAL 95 DAY,  CURDATE() + INTERVAL 270 DAY, 'TF-3320',     '', 2),
    ('Rabia',                             CURDATE() - INTERVAL 380 DAY, CURDATE() - INTERVAL 15 DAY,  'RB-2025-870', 'Refuerzo vencido.', 3),
    ('Triple felina',                     CURDATE() - INTERVAL 45 DAY,  CURDATE() + INTERVAL 3 DAY,   'TF-3321',     '', 4),
    ('Desparasitación',                   CURDATE() - INTERVAL 70 DAY,  CURDATE() + INTERVAL 20 DAY,  '',            'Antiparasitario oral.', 5),
    ('Rabia',                             CURDATE() - INTERVAL 300 DAY, CURDATE() + INTERVAL 65 DAY,  'RB-2026-020', '', 6),
    ('Leucemia felina',                   CURDATE() - INTERVAL 340 DAY, CURDATE() + INTERVAL 25 DAY,  'LF-778',      '', 7);

INSERT INTO notificacion (tipo, destinatario, asunto, estado, detalle_error, fecha_envio, id_cita, id_vacuna) VALUES
    ('confirmacion', 'maria.lopez@ejemplo.com', 'Confirmación de cita para Luna', 'enviado', '', UTC_TIMESTAMP(6) - INTERVAL 2 DAY, 11, NULL),
    ('confirmacion', 'jose.perez@ejemplo.com',  'Confirmación de cita para Rocky', 'enviado', '', UTC_TIMESTAMP(6) - INTERVAL 1 DAY, 12, NULL);

-- =====================================================================
-- 6. VISTAS (consultas listas para reportes, Workbench o Excel)
-- =====================================================================

-- Detalle completo de cada cita con paciente, propietario y veterinario
CREATE OR REPLACE VIEW v_citas_detalle AS
SELECT  c.id_cita,
        c.fecha_cita,
        TIME_FORMAT(c.hora_inicio, '%H:%i')                                      AS hora_inicio,
        TIME_FORMAT(COALESCE(c.hora_fin, ADDTIME(c.hora_inicio, '00:30:00')), '%H:%i') AS hora_fin,
        c.estado,
        c.tipo_cita,
        c.motivo,
        p.id_paciente,
        p.nombre        AS paciente,
        p.especie,
        p.raza,
        p.alergias,
        pr.id_propietario,
        pr.nombre       AS propietario,
        pr.telefono,
        pr.email,
        v.id_veterinario,
        v.nombre_completo AS veterinario
FROM cita c
JOIN paciente    p  ON p.id_paciente     = c.id_paciente
JOIN propietario pr ON pr.id_propietario = p.id_propietario
JOIN veterinario v  ON v.id_veterinario  = c.id_veterinario;

-- Agenda del día (HU-09)
CREATE OR REPLACE VIEW v_agenda_hoy AS
SELECT * FROM v_citas_detalle
WHERE fecha_cita = CURDATE() AND estado <> 'cancelada'
ORDER BY hora_inicio;

-- Tendencia mensual de citas por estado (RF-20)
CREATE OR REPLACE VIEW v_resumen_mensual_citas AS
SELECT  DATE_FORMAT(fecha_cita, '%Y-%m')          AS mes,
        COUNT(*)                                  AS total,
        SUM(estado = 'pendiente')                 AS pendientes,
        SUM(estado = 'confirmada')                AS confirmadas,
        SUM(estado = 'completada')                AS completadas,
        SUM(estado = 'cancelada')                 AS canceladas,
        ROUND(100 * SUM(estado = 'cancelada') / COUNT(*), 1) AS porcentaje_cancelacion
FROM cita
GROUP BY DATE_FORMAT(fecha_cita, '%Y-%m')
ORDER BY mes;

-- Vacunas vencidas o que vencen en los próximos 30 días
CREATE OR REPLACE VIEW v_vacunas_por_vencer AS
SELECT  va.id_vacuna,
        va.nombre AS vacuna,
        va.fecha_aplicacion,
        va.fecha_proxima,
        DATEDIFF(va.fecha_proxima, CURDATE()) AS dias_restantes,
        CASE WHEN va.fecha_proxima < CURDATE() THEN 'VENCIDA' ELSE 'PRÓXIMA' END AS situacion,
        p.nombre  AS paciente,
        pr.nombre AS propietario,
        pr.telefono,
        pr.email
FROM vacuna va
JOIN paciente    p  ON p.id_paciente     = va.id_paciente
JOIN propietario pr ON pr.id_propietario = p.id_propietario
WHERE va.fecha_proxima IS NOT NULL
  AND va.fecha_proxima <= CURDATE() + INTERVAL 30 DAY
ORDER BY va.fecha_proxima;

-- Indicadores del panel principal en una sola fila (RF-18)
CREATE OR REPLACE VIEW v_indicadores_panel AS
SELECT
    (SELECT COUNT(*) FROM cita WHERE fecha_cita = CURDATE() AND estado <> 'cancelada')              AS citas_hoy,
    (SELECT COUNT(*) FROM cita WHERE estado = 'pendiente' AND fecha_cita >= CURDATE())               AS citas_pendientes,
    (SELECT COUNT(*) FROM cita WHERE DATE_FORMAT(fecha_cita, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
                                 AND estado <> 'cancelada')                                          AS citas_mes,
    (SELECT COUNT(*) FROM paciente)                                                                  AS total_pacientes,
    (SELECT COUNT(*) FROM propietario)                                                               AS total_propietarios,
    (SELECT COUNT(*) FROM veterinario WHERE activo = 1)                                              AS veterinarios_activos,
    (SELECT COUNT(*) FROM cita WHERE fecha_cita = CURDATE() AND estado = 'completada')               AS completadas_hoy;

-- Efectividad de las notificaciones (indicador de la variable dependiente 3)
CREATE OR REPLACE VIEW v_efectividad_notificaciones AS
SELECT  tipo,
        COUNT(*)                                     AS total,
        SUM(estado = 'enviado')                      AS enviados,
        SUM(estado = 'error')                        AS con_error,
        ROUND(100 * SUM(estado = 'enviado') / COUNT(*), 1) AS porcentaje_exito
FROM notificacion
GROUP BY tipo;


-- =====================================================================
-- 7. PROCEDIMIENTOS ALMACENADOS
-- =====================================================================
DELIMITER $$

-- Devuelve las citas que chocan con el horario indicado (RF-10).
-- Ejemplo: CALL sp_verificar_disponibilidad(1, CURDATE(), '09:15', '09:45', NULL);
CREATE PROCEDURE sp_verificar_disponibilidad(
    IN p_id_veterinario INT,
    IN p_fecha          DATE,
    IN p_hora_inicio    TIME,
    IN p_hora_fin       TIME,
    IN p_excluir_cita   INT
)
BEGIN
    DECLARE v_fin TIME;
    SET v_fin = COALESCE(p_hora_fin, ADDTIME(p_hora_inicio, '00:30:00'));

    SELECT c.id_cita, c.fecha_cita, c.hora_inicio,
           COALESCE(c.hora_fin, ADDTIME(c.hora_inicio, '00:30:00')) AS hora_fin,
           p.nombre AS paciente, c.estado
    FROM cita c
    JOIN paciente p ON p.id_paciente = c.id_paciente
    WHERE c.id_veterinario = p_id_veterinario
      AND c.fecha_cita     = p_fecha
      AND c.estado        <> 'cancelada'
      AND (p_excluir_cita IS NULL OR c.id_cita <> p_excluir_cita)
      AND p_hora_inicio < COALESCE(c.hora_fin, ADDTIME(c.hora_inicio, '00:30:00'))
      AND c.hora_inicio < v_fin;
END$$

-- Reporte de citas por estado, tipo y veterinario en un período (RF-19, RF-21).
-- Ejemplo: CALL sp_reporte_citas_periodo('2026-01-01', '2026-12-31');
CREATE PROCEDURE sp_reporte_citas_periodo(IN p_inicio DATE, IN p_fin DATE)
BEGIN
    SELECT 'Por estado' AS agrupacion, estado AS valor, COUNT(*) AS total
      FROM cita WHERE fecha_cita BETWEEN p_inicio AND p_fin GROUP BY estado
    UNION ALL
    SELECT 'Por tipo', IF(tipo_cita = '', 'Sin tipo', tipo_cita), COUNT(*)
      FROM cita WHERE fecha_cita BETWEEN p_inicio AND p_fin GROUP BY tipo_cita
    UNION ALL
    SELECT 'Por veterinario', v.nombre_completo, COUNT(*)
      FROM cita c JOIN veterinario v ON v.id_veterinario = c.id_veterinario
     WHERE c.fecha_cita BETWEEN p_inicio AND p_fin GROUP BY v.nombre_completo
    ORDER BY agrupacion, total DESC;
END$$

-- Agenda de un veterinario para una fecha (HU-09).
-- Ejemplo: CALL sp_agenda_veterinario(1, CURDATE());
CREATE PROCEDURE sp_agenda_veterinario(IN p_id_veterinario INT, IN p_fecha DATE)
BEGIN
    SELECT hora_inicio, hora_fin, paciente, especie, alergias, propietario, telefono, motivo, estado
    FROM v_citas_detalle
    WHERE id_veterinario = p_id_veterinario AND fecha_cita = p_fecha AND estado <> 'cancelada'
    ORDER BY hora_inicio;
END$$


-- =====================================================================
-- 8. TRIGGERS — Segunda barrera contra citas duplicadas (RF-10)
--    Aunque la aplicación ya valida la disponibilidad, estos triggers
--    impiden a nivel de base de datos que un veterinario tenga dos citas
--    activas que se traslapen, incluso si se inserta desde otro programa.
-- =====================================================================
CREATE TRIGGER trg_cita_validar_insert
BEFORE INSERT ON cita
FOR EACH ROW
BEGIN
    IF NEW.estado <> 'cancelada' AND EXISTS (
        SELECT 1 FROM cita c
        WHERE c.id_veterinario = NEW.id_veterinario
          AND c.fecha_cita     = NEW.fecha_cita
          AND c.estado        <> 'cancelada'
          AND NEW.hora_inicio  < COALESCE(c.hora_fin, ADDTIME(c.hora_inicio, '00:30:00'))
          AND c.hora_inicio    < COALESCE(NEW.hora_fin, ADDTIME(NEW.hora_inicio, '00:30:00'))
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No se puede agendar: el veterinario ya tiene una cita en ese dia y hora.';
    END IF;
END$$

CREATE TRIGGER trg_cita_validar_update
BEFORE UPDATE ON cita
FOR EACH ROW
BEGIN
    IF NEW.estado <> 'cancelada' AND EXISTS (
        SELECT 1 FROM cita c
        WHERE c.id_cita       <> NEW.id_cita
          AND c.id_veterinario = NEW.id_veterinario
          AND c.fecha_cita     = NEW.fecha_cita
          AND c.estado        <> 'cancelada'
          AND NEW.hora_inicio  < COALESCE(c.hora_fin, ADDTIME(c.hora_inicio, '00:30:00'))
          AND c.hora_inicio    < COALESCE(NEW.hora_fin, ADDTIME(NEW.hora_inicio, '00:30:00'))
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No se puede modificar: el veterinario ya tiene una cita en ese dia y hora.';
    END IF;
END$$

DELIMITER ;

-- =====================================================================
-- 9. VERIFICACIÓN RÁPIDA
-- =====================================================================
SELECT 'Usuarios' AS tabla, COUNT(*) AS registros FROM auth_user
UNION ALL SELECT 'Roles', COUNT(*) FROM auth_group
UNION ALL SELECT 'Propietarios', COUNT(*) FROM propietario
UNION ALL SELECT 'Pacientes', COUNT(*) FROM paciente
UNION ALL SELECT 'Veterinarios', COUNT(*) FROM veterinario
UNION ALL SELECT 'Citas', COUNT(*) FROM cita
UNION ALL SELECT 'Vacunas', COUNT(*) FROM vacuna;

SELECT * FROM v_indicadores_panel;
SELECT * FROM v_agenda_hoy;

-- Prueba del trigger (CP-08): descomente y ejecute; debe fallar con el mensaje del trigger.
-- INSERT INTO cita (fecha_cita, hora_inicio, hora_fin, motivo, tipo_cita, estado, notas,
--                   fecha_creacion, fecha_actualizacion, id_paciente, id_veterinario)
-- VALUES (CURDATE(), '09:10', '09:40', 'Prueba de traslape', 'consulta', 'pendiente', '',
--         UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1, 1);
