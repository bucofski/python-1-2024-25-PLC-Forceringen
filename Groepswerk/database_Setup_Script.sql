-- =============================================
-- TABLE CREATION
-- =============================================

DROP TABLE IF EXISTS bit_force_reason, resource_bit, plc_resource, resource, plc CASCADE;

-- 1. PLC table: each PLC is unique
CREATE TABLE plc (
    plc_id SERIAL PRIMARY KEY,
    plc_name VARCHAR(100) NOT NULL UNIQUE
);

-- 2. Resource table: resources can be shared among PLCs
CREATE TABLE resource (
    resource_id SERIAL PRIMARY KEY,
    resource_name VARCHAR(100) NOT NULL UNIQUE
);

-- 3. Association of PLC and Resource (many-to-many if needed, or one-to-many if each PLC has one resource)
-- If each PLC has exactly one resource, use a foreign key in plc; otherwise use this join table.
CREATE TABLE plc_resource (
    plc_id INTEGER NOT NULL REFERENCES plc(plc_id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resource(resource_id) ON DELETE CASCADE,
    PRIMARY KEY (plc_id, resource_id)
);

-- 4. Bit entries: each bit is defined by a bit_number within a resource
-- The same bit_number text (e.g. 'W1000') can occur in different resources
CREATE TABLE resource_bit (
    bit_id SERIAL PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resource(resource_id) ON DELETE CASCADE,
    bit_number VARCHAR(20) NOT NULL,
    kks VARCHAR(50) NOT NULL UNIQUE,
    comment TEXT,
    second_comment TEXT,
    value VARCHAR(50),
    UNIQUE (resource_id, bit_number)
);

-- 5. Forced reasons: track why a bit is forced
CREATE TABLE bit_force_reason (
    force_id SERIAL PRIMARY KEY,
    bit_id INTEGER NOT NULL REFERENCES resource_bit(bit_id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    forced_by VARCHAR(100),
    forced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- ADD DATA
-- =============================================

-- Insert unique PLC entries
INSERT INTO plc (plc_name)
VALUES
    ('S1E'), ('S1C'), ('S1K'), ('S1S'),
    ('S2E'), ('S2C'), ('S2K'), ('S2S'),
    ('S3E'), ('S3C'), ('S3K'), ('S3S'),
    ('BTEST');

-- Insert unique resource entries
INSERT INTO resource (resource_name)
VALUES
    ('1'), ('2'), ('3'), ('4'), ('5'),
    ('6'), ('7'), ('8'), ('9'), ('10'),
    ('KMOR'), ('NIET'), ('WT1');

-- Example: Map PLCs to their resources (assuming each PLC has multiple resources)
-- NOTE: The `plc_id` and `resource_id` should align with the corresponding table entries
INSERT INTO plc_resource (plc_id, resource_id)
VALUES
    (1, 1), -- Map PLC 'S1E' (plc_id=1) with all the needed resources
    (1, 2),
    (1, 3),
    (1, 4),
    (2, 1), -- Map PLC 'S1C' (plc_id=2) with all the needed resources
    (2, 2),
    (2, 3),
    (2, 4),
    (3, 1), -- Map PLC 'S1K' (plc_id=3) with all the needed resources
    (3, 2),
    (3, 3),
    (3, 4),
    (4, 1), -- Map PLC 'S1S' (plc_id=4) with all the needed resources
    (4, 2),
    (4, 3),
    (4, 4),
    (5, 1), -- Map PLC 'S2E' (plc_id=5) with all the needed resources
    (5, 2),
    (5, 3),
    (5, 4),
    (6, 1), -- Map PLC 'S2C' (plc_id=6) with all the needed resources
    (6, 2),
    (6, 3),
    (6, 4),
    (7, 1), -- Map PLC 'S2K' (plc_id=7) with all the needed resources
    (7, 2),
    (7, 3),
    (7, 4),
    (8, 1), -- Map PLC 'S2S' (plc_id=8) with all the needed resources
    (8, 2),
    (8, 3),
    (8, 4),
    (9, 1), -- Map PLC 'S3E' (plc_id=9) with all the needed resources
    (9, 2),
    (9, 3),
    (9, 4),
    (10, 1), -- Map PLC 'S3C' (plc_id=10) with all the needed resources
    (10, 2),
    (10, 3),
    (10, 4),
    (11, 1), -- Map PLC 'S3K' (plc_id=11) with all the needed resources
    (11, 2),
    (11, 3),
    (11, 4),
    (12, 1), -- Map PLC 'S3S' (plc_id=12) with all the needed resources
    (12, 2),
    (12, 3),
    (12, 4),
    (13, 11), -- Map PLC 'BTEST' (plc_id=13) with its unique resources
    (13, 12),
    (13, 13);

-- =============================================
-- SAMPLE DATA
-- =============================================

WITH res_id AS (
    SELECT resource_id FROM resource WHERE resource_name = 'NIET'
)
INSERT INTO resource_bit (resource_id, bit_number, kks, comment, second_comment, value)
VALUES
(
    (SELECT resource_id FROM res_id),
    'R01420',
    'SIDTOVY.Test.Override3',
    'None',
    'None',
    '4640e400'
),
(
    (SELECT resource_id FROM res_id),
    'W00872',
    'PilootTD.Interlock.VrijgaveBewegen_KOPPELZO',
    'Vrijgave Bewegen Koppelzone',
    '[TD2,TDS,1201]',
    '0'
);

-- =============================================
-- QUERRY
-- =============================================

SELECT
    p.plc_name,
    r.resource_name AS resource,
    rb.bit_number AS variable_name_id,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
WHERE r.resource_name = 'NIET'
ORDER BY p.plc_name, rb.bit_number;

-- =============================================
-- VIEUWS - PLC
-- =============================================

-- View for PLC 'S1E'
DROP VIEW IF EXISTS view_plc_s1e;
CREATE VIEW view_plc_s1e AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S1E'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S1C'
DROP VIEW IF EXISTS view_plc_s1c;
CREATE VIEW view_plc_s1c AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S1C'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S1K'
DROP VIEW IF EXISTS view_plc_s1k;
CREATE VIEW view_plc_s1k AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S1K'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S1S'
DROP VIEW IF EXISTS view_plc_s1s;
CREATE VIEW view_plc_s1s AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S1S'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S2E'
DROP VIEW IF EXISTS view_plc_s2e;
CREATE VIEW view_plc_s2e AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S2E'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S2C'
DROP VIEW IF EXISTS view_plc_s2c;
CREATE VIEW view_plc_s2c AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S2C'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S2K'
DROP VIEW IF EXISTS view_plc_s2k;
CREATE VIEW view_plc_s2k AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S2K'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S2S'
DROP VIEW IF EXISTS view_plc_s2s;
CREATE VIEW view_plc_s2s AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S2S'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S3E'
DROP VIEW IF EXISTS view_plc_s3e;
CREATE VIEW view_plc_s3e AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S3E'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S3C'
DROP VIEW IF EXISTS view_plc_s3c;
CREATE VIEW view_plc_s3c AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S3C'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S3K'
DROP VIEW IF EXISTS view_plc_s3k;
CREATE VIEW view_plc_s3k AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S3K'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'S3S'
DROP VIEW IF EXISTS view_plc_s3s;
CREATE VIEW view_plc_s3s AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'S3S'
ORDER BY r.resource_name, rb.bit_number;

-- View for PLC 'BTEST'
DROP VIEW IF EXISTS view_plc_btest;
CREATE VIEW view_plc_btest AS
SELECT
    p.plc_name AS PLC,
    r.resource_name AS resource,
    rb.bit_number AS variable,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    bfr.forced_by,
    bfr.forced_at
FROM resource r
JOIN plc_resource pr ON r.resource_id = pr.resource_id
JOIN plc p ON pr.plc_id = p.plc_id
JOIN resource_bit rb ON rb.resource_id = r.resource_id
LEFT JOIN bit_force_reason bfr ON bfr.bit_id = rb.bit_id
WHERE p.plc_name = 'BTEST'
ORDER BY r.resource_name, rb.bit_number;