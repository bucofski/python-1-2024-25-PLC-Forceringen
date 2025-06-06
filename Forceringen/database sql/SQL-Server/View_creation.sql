-- =============================================
-- Call view variables PLC met date - SQL Server version
-- =============================================

IF OBJECT_ID('plc_bits', 'V') IS NOT NULL DROP VIEW plc_bits;
GO

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
WHERE b.force_active = 1;
-- Note: ORDER BY removed from view as SQL Server doesn't allow it in views without TOP
GO

-- =============================================
-- Call view variables PLC
-- =============================================

SELECT *
FROM plc_bits
WHERE PLC = 'BTEST'
ORDER BY PLC, resource, bit_number;

-- =============================================
-- Call view variables PLC and resource
-- =============================================

SELECT *
FROM plc_bits  -- Changed from resource_bit to plc_bits as the original query seems to have an error
WHERE PLC = 'BTEST'
  AND resource = 'NIET'
ORDER BY bit_number;

-- =============================================
-- PLC All detail variables view - SQL Server version
-- =============================================

IF OBJECT_ID('last_5_force_reasons_per_bit', 'V') IS NOT NULL DROP VIEW last_5_force_reasons_per_bit;
GO

CREATE VIEW last_5_force_reasons_per_bit AS
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
WHERE bfr.rn BETWEEN 2 AND 6;
-- Note: ORDER BY removed from view as SQL Server doesn't allow it in views without TOP
GO

-- =============================================
-- Call detail view variables PLC and resource
-- =============================================

SELECT *
FROM last_5_force_reasons_per_bit
WHERE PLC = 'BTEST'
  AND resource = 'NIET'
  AND bit_number = 'placeholder'
ORDER BY bit_id, forced_at DESC;