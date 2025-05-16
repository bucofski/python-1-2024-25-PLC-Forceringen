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
-- The same bit_number text (e.g., 'W1000') can occur in different resources
CREATE TABLE resource_bit (
    bit_id SERIAL PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resource(resource_id) ON DELETE CASCADE,
    bit_number VARCHAR(20) NOT NULL,
    kks VARCHAR(50) NOT NULL UNIQUE,
    comment TEXT,
    second_comment TEXT,
    value VARCHAR(50),
    Forced_Status BOOLEAN DEFAULT TRUE, -- Added Forced_Status column
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
-- TRIGGER FUNCTION TO HANDLE FORCED_STATUS UPDATES
-- =============================================

CREATE OR REPLACE FUNCTION update_forced_status_per_plc()
RETURNS TRIGGER AS $$
DECLARE
    plc_id_to_update INTEGER;
BEGIN
    -- Step 1: Determine the plc_id that corresponds to the resource_id in the row being written
    SELECT plc_id INTO plc_id_to_update
    FROM plc_resource
    WHERE resource_id = NEW.resource_id
    LIMIT 1;

    -- Step 2: Set Forced_Status = FALSE for all existing rows for the same PLC
    UPDATE resource_bit
    SET Forced_Status = FALSE
    WHERE resource_id IN (
        SELECT resource_id
        FROM plc_resource
        WHERE plc_id = plc_id_to_update
    )
    AND bit_id NOT IN (
        -- Exclude the rows being inserted/updated in this transaction
        SELECT bit_id FROM resource_bit WHERE resource_id = NEW.resource_id
    );

    -- Step 3: Update the row being inserted/updated, ensuring it is marked Forced_Status = TRUE
    NEW.Forced_Status := TRUE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- TRIGGER TO APPLY THE FUNCTION
-- =============================================

-- Drop the existing trigger if it exists
DROP TRIGGER IF EXISTS trigger_update_forced_status ON resource_bit;

-- Create the trigger to fire AFTER INSERT or UPDATE operations
CREATE TRIGGER trigger_update_forced_status
AFTER INSERT OR UPDATE ON resource_bit
FOR EACH ROW
EXECUTE FUNCTION update_forced_status_per_plc();

-- =============================================
-- INSERT INITIAL DATA
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
-- SAMPLE DATA FOR TRIGGER
-- =============================================

-- Insert sample data for Resource 1
INSERT INTO resource_bit (resource_id, bit_number, kks, comment, second_comment, value)
VALUES
    (1, 'W2000', 'KKS_001', 'Common Comment 1', 'Second Common Comment 1', 'Value A'),
    (1, 'W2001', 'KKS_002', 'Common Comment 2', 'Second Common Comment 2', 'Value B'),
    (1, 'W3000', 'KKS_003', 'Resource 1 - Unique Comment 1', 'Second R1 Comment 1', 'Value C'),
    (1, 'W3001', 'KKS_004', 'Resource 1 - Unique Comment 2', 'Second R1 Comment 2', 'Value D'),
    (1, 'W3002', 'KKS_005', 'Resource 1 - Unique Comment 3', 'Second R1 Comment 3', 'Value E');

-- Insert sample data for Resource 2
INSERT INTO resource_bit (resource_id, bit_number, kks, comment, second_comment, value)
VALUES
    (2, 'W2000', 'KKS_006', 'Common Comment 1', 'Second Common Comment 1', 'Value F'),
    (2, 'W2001', 'KKS_007', 'Common Comment 2', 'Second Common Comment 2', 'Value G'),
    (2, 'W3003', 'KKS_008', 'Resource 2 - Unique Comment 1', 'Second R2 Comment 1', 'Value H'),
    (2, 'W3004', 'KKS_009', 'Resource 2 - Unique Comment 2', 'Second R2 Comment 2', 'Value I'),
    (2, 'W3005', 'KKS_010', 'Resource 2 - Unique Comment 3', 'Second R2 Comment 3', 'Value J');

-- Insert sample data for Resource 3
INSERT INTO resource_bit (resource_id, bit_number, kks, comment, second_comment, value)
VALUES
    (3, 'W2000', 'KKS_011', 'Common Comment 1', 'Second Common Comment 1', 'Value K'),
    (3, 'W2001', 'KKS_012', 'Common Comment 2', 'Second Common Comment 2', 'Value L'),
    (3, 'W3006', 'KKS_013', 'Resource 3 - Unique Comment 1', 'Second R3 Comment 1', 'Value M'),
    (3, 'W3007', 'KKS_014', 'Resource 3 - Unique Comment 2', 'Second R3 Comment 2', 'Value N'),
    (3, 'W3008', 'KKS_015', 'Resource 3 - Unique Comment 3', 'Second R3 Comment 3', 'Value O');

SELECT
    r.resource_name AS resource,
    rb.bit_number,
    rb.kks,
    rb.comment,
    rb.second_comment,
    rb.value,
    rb.Forced_Status
FROM
    resource_bit rb
JOIN
    resource r ON rb.resource_id = r.resource_id
JOIN
    plc_resource pr ON r.resource_id = pr.resource_id
JOIN
    plc p ON pr.plc_id = p.plc_id
WHERE
    p.plc_name = 'BTEST'
ORDER BY
    r.resource_name, rb.bit_number;
