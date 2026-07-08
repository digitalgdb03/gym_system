-- Plantilla reutilizable: registrar membresias (planes ya pagados) para
-- clientes EXISTENTES, dando solo cedula + plan + fecha inicio + fecha fin.
--
-- Uso: agrega una fila por cliente/plan en tmp_membresias_nuevas y corre
-- todo el script. Es idempotente (no duplica si lo corres de nuevo con
-- las mismas filas) y reactiva a ACTIVO al cliente si estaba Moroso.
--
-- Referencia rapida:
--   service_name: Pesas | Boxeo | MMA | Bailoterapia | Combinados
--   duration:     DAILY | WEEKLY | MONTHLY
--   plan_name:    '' para planes simples (Pesas/Boxeo/MMA/Bailoterapia)
--                 nombre EXACTO del combo para Combinados, por ejemplo:
--                 'MMA + Pesas (afiliados)', 'Boxeo + Pesas (afiliados)',
--                 'Pesas + Boxeo', 'Pesas + MMA', 'Boxeo personalizado',
--                 'Boxeo personalizado + Pesas'

BEGIN;

CREATE TEMP TABLE tmp_membresias_nuevas (
    id_card      VARCHAR(20),
    service_name VARCHAR(80),
    duration     VARCHAR(10),
    plan_name    VARCHAR(120),
    start_date   DATE,
    end_date     DATE
) ON COMMIT DROP;

-- ============================================================
-- DATOS A COMPLETAR: una fila por cada (cedula, plan, inicio, fin)
-- ============================================================
INSERT INTO tmp_membresias_nuevas (id_card, service_name, duration, plan_name, start_date, end_date) VALUES
    ('12345678', 'Boxeo', 'MONTHLY', '', DATE '2026-07-01', DATE '2026-07-31'),
    ('87654321', 'MMA',   'WEEKLY',  '', DATE '2026-07-05', DATE '2026-07-12');

-- ============================================================
-- CHEQUEO (opcional, corre esto antes de seguir): filas que no van a
-- insertarse porque la cedula o el plan no existen en la base de datos.
-- Si esta consulta devuelve algo, revisa la cedula/service_name/duration/
-- plan_name antes de continuar.
-- ============================================================
SELECT t.*,
       (c.id IS NULL) AS cliente_no_encontrado,
       (p.id IS NULL) AS plan_no_encontrado
FROM tmp_membresias_nuevas t
LEFT JOIN client_client c ON c.doc_type = 'V' AND c.id_card = t.id_card
LEFT JOIN services_service s ON s.name = t.service_name
LEFT JOIN plans_plan p ON p.service_id = s.id AND p.duration = t.duration AND p.name = t.plan_name
WHERE c.id IS NULL OR p.id IS NULL;

-- ============================================================
-- INSERTA LAS MEMBRESIAS (tabla: client_membership)
-- ============================================================
INSERT INTO client_membership (client_id, plan_id, start_date, end_date, is_custom, currency, days)
SELECT c.id, p.id, t.start_date, t.end_date, false, 'BCV', 0
FROM tmp_membresias_nuevas t
JOIN client_client c ON c.doc_type = 'V' AND c.id_card = t.id_card
JOIN services_service s ON s.name = t.service_name
JOIN plans_plan p ON p.service_id = s.id AND p.duration = t.duration AND p.name = t.plan_name
WHERE NOT EXISTS (
    SELECT 1 FROM client_membership m
    WHERE m.client_id = c.id AND m.plan_id = p.id
      AND m.start_date = t.start_date AND m.end_date = t.end_date
);

-- ============================================================
-- REACTIVA a ACTIVO a los clientes de la lista que estaban Morosos
-- ============================================================
UPDATE client_client c
SET status = 'ACTIVE'
FROM tmp_membresias_nuevas t
WHERE c.doc_type = 'V' AND c.id_card = t.id_card AND c.status = 'OVERDUE';

COMMIT;
