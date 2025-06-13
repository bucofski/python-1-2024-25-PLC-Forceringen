-- =============================================
-- Call view variables PLC met date - SQL Server version (Updated for new schema)
-- =============================================

IF OBJECT_ID('plc_bits', 'V') IS NOT NULL DROP VIEW plc_bits;
GO

CREATE VIEW plc_bits AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    b.bit_number,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.var_type,
    fr.value,  -- Now comes from bit_force_reason table
    rb.force_active,
    CONVERT(DATETIME, fr.forced_at) AS forced_at,  -- Convert DATETIMEOFFSET to DATETIME
    fr.forced_by,
    fr.melding,
    fr.reason
FROM resource_bit rb
JOIN plc p ON p.plc_id = rb.plc_id
JOIN resource r ON r.resource_id = rb.resource_id
JOIN bit b ON b.bit_id = rb.bit_id  -- Join with bit table to get bit_number
LEFT JOIN bit_force_reason fr ON fr.resource_bit_id = rb.resource_bit_id  -- Updated to use resource_bit_id
    AND fr.force_id = (
        SELECT MAX(fr2.force_id)
        FROM bit_force_reason fr2
        WHERE fr2.resource_bit_id = rb.resource_bit_id  -- Updated to use resource_bit_id
    )
WHERE rb.force_active = 1;
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
    rb.resource_bit_id,
    b.bit_number,  -- Access bit_number from bit table
    rb.kks,
    bfr.value,  -- Added value from bit_force_reason table
    CONVERT(DATETIME, bfr.forced_at) as forced_at,
    CONVERT(DATETIME, bfr.deforced_at) as deforced_at,
    bfr.forced_by,
    bfr.reason
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY resource_bit_id  -- Use resource_bit_id for partitioning
               ORDER BY force_id DESC
           ) as rn
      FROM bit_force_reason
) bfr
JOIN resource_bit rb ON bfr.resource_bit_id = rb.resource_bit_id  -- Join on resource_bit_id
JOIN bit b ON rb.bit_id = b.bit_id  -- Join with bit table to get bit_number
JOIN plc p ON rb.plc_id = p.plc_id
JOIN resource r ON rb.resource_id = r.resource_id
WHERE bfr.rn BETWEEN 2 AND 6;
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