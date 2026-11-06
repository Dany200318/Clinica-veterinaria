-- =====================================================================
--  SISTEMA WEB DE GESTIÓN PARA UNA VETERINARIA
--  Script 03 — Objetos adicionales: vistas, procedimientos y triggers
--
--  Úselo SOLO si creó las tablas con «python manage.py migrate» (camino A
--  del README). Si importó 02_clinica_veterinaria_completa.sql, estos
--  objetos ya existen.
--  Ejecutar como root:  mysql -u root -p clinica_veterinaria < 03_objetos_adicionales.sql
-- =====================================================================
USE clinica_veterinaria;

DROP TRIGGER  IF EXISTS trg_cita_validar_insert;
DROP TRIGGER  IF EXISTS trg_cita_validar_update;
DROP PROCEDURE IF EXISTS sp_verificar_disponibilidad;
DROP PROCEDURE IF EXISTS sp_reporte_citas_periodo;
DROP PROCEDURE IF EXISTS sp_agenda_veterinario;

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

