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

SELECT * 
FROM bit_force_reason
select * from resource, plc
-- =============================================
-- Call view variables PLC and resource
-- =============================================

SELECT * 
FROM resource_bit
WHERE PLC = 'BTEST'
  AND resource = 'NIET';

update resource_bit
set bit_number = 1200 where bit_id = 7
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
WHERE bfr.rn <= 5
ORDER BY rb.bit_id, bfr.force_id DESC;

-- =============================================
-- Call detail view variables PLC and resource
-- =============================================

SELECT *
FROM last_5_force_reasons_per_bit
WHERE PLC = 'BTEST'
  AND resource = 'NIET'
  AND bit_number = 'placeholder';


CREATE OR REPLACE VIEW last_5_bit_forcings AS
SELECT
    rbit.bit_id,
    p.plc_name,
    r.resource_name,
    rbit.bit_number,
    rbit.kks,
    rbit.comment,
    rbit.value,
    rbit.force_active,
    rbit.forced_at,
    bfr.reason,
    bfr.forced_by,
    bfr.deforced_at
FROM
    bit_force_reason bfr
JOIN
    resource_bit rbit ON bfr.bit_id = rbit.bit_id
JOIN
    plc p ON rbit.plc_id = p.plc_id
JOIN
    resource r ON rbit.resource_id = r.resource_id
ORDER BY
    bfr.force_id DESC
LIMIT 5;

-- =============================================
-- Call detail view variables PLC and resource
-- =============================================
SELECT *
FROM last_5_bit_forcings
WHERE plc = 'BTEST'
  AND resource_name = 'NIET'
  AND bit_number = 'Your_Bit_Number'; -- optional, if you want to filter for a specific bit number

-- Simplified testing query for ad-hoc use (no view creation)
SELECT 
    p.plc_name AS "PLC",
    r.resource_name AS "Resource"
FROM 
    plc p
JOIN 
    resource r ON 1=1
WHERE 
    (p.plc_name, r.resource_name) IN (
        -- YAML configuration pairings from AFV
        ('AFV', 'Insp'), ('AFV', 'House'), ('AFV', 'UitSeq'),
        -- YAML configuration pairings from REG
        ('REG', 'House'),
        -- YAML configuration pairings from BTEST
        ('BTEST', 'NIET'), ('BTEST', 'KMOR'), ('BTEST', 'WT1')
    )
ORDER BY 
    p.plc_name, r.resource_name;

 select * from plc
 select * from resource


UPDATE bit_force_reason AS bfr
SET reason = 'test123'
FROM resource_bit rb
JOIN plc p      ON rb.plc_id       = p.plc_id
JOIN resource r ON rb.resource_id  = r.resource_id
WHERE bfr.bit_id       = rb.bit_id
  AND p.plc_name       = 'BTEST'
  AND r.resource_name  = 'NIET' 
  AND rb.bit_number    = 'I00000'
RETURNING
  bfr.force_id,        -- now unambiguous
  rb.bit_number, 
  bfr.reason;
