-- =============================================
-- Call view variables PLC met date
-- =============================================

DROP VIEW IF EXISTS plc_bits;
CREATE VIEW plc_bits AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    b.bit_number,
    b.kks,
    b.comment,
    b.second_comment,
	b.var_type,
    b.value,
    b.force_active,
    fr.forced_at AS forced_at,
	fr.forced_by,
    fr.reason
FROM resource_bit b
JOIN plc p ON p.plc_id = b.plc_id
JOIN resource r ON r.resource_id = b.resource_id
LEFT JOIN bit_force_reason fr ON fr.bit_id = b.bit_id
    AND fr.force_id = (
        SELECT MAX(fr2.force_id)
        FROM bit_force_reason fr2
        WHERE fr2.bit_id = b.bit_id
    )
ORDER BY p.plc_name, r.resource_name, b.bit_number;



-- =============================================
-- Call view variables PLC
-- =============================================

SELECT *
FROM plc_bits
WHERE plc = 'BTEST';

-- =============================================
-- Call view variables PLC and resource
-- =============================================

SELECT *
FROM resource_bit
WHERE PLC = 'BTEST'
  AND resource = 'NIET';

-- =============================================
-- PLC All detail variables view
-- =============================================
DROP VIEW IF EXISTS last_5_force_reasons_per_bit;
CREATE OR REPLACE VIEW last_5_force_reasons_per_bit AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_id,
    rb.bit_number,
    rb.kks,
    bfr.forced_at,
    bfr.deforced_at,
    bfr.forced_by,
    bfr.reason
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY bit_id
               ORDER BY force_id DESC
           ) as rn
      FROM bit_force_reason
) bfr
JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
JOIN plc p ON rb.plc_id = p.plc_id
JOIN resource r ON rb.resource_id = r.resource_id
WHERE bfr.rn BETWEEN 2 AND 6
ORDER BY rb.bit_id, bfr.force_id DESC;

-- =============================================
-- Call detail view variables PLC and resource
-- =============================================

SELECT *
FROM last_5_force_reasons_per_bit
WHERE PLC = 'BTEST'
  AND resource = 'NIET'
  AND bit_number = 'placeholder';
