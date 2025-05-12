-- ==========================
-- CREATE UNIFIED TABLE
-- ==========================
CREATE TABLE unified_data (
    department_name VARCHAR(255) NOT NULL,    -- E.g., Sidgal
    plc_name VARCHAR(255) NOT NULL,           -- E.g., S1E
    resource_number VARCHAR(50) NOT NULL,     -- Resource number (e.g., numeric or text - NIET, KMOR, WT1)
    full_resource_name VARCHAR(255) AS (plc_name || resource_number) STORED, -- Auto-computed column combining plc_name and resource_number
    variable_name_id VARCHAR(255),            -- Unique identifier for the variable (e.g., G00001)
    KKS VARCHAR(255),                         -- KKS identifier for the variable (e.g., House.Output.KKS1)
    comment TEXT,                             -- Comment for the variable
    second_comment TEXT,                      -- Secondary comment for the variable
    variable_type VARCHAR(50),                -- Data type of the variable (e.g., LINT, BOOL)
    variable_value DOUBLE PRECISION,          -- Value of the variable
    UNIQUE (plc_name, full_resource_name, variable_name_id) -- Unique key to avoid duplicates
);

-- ==========================
-- INSERT ALL DATA INTO UNIFIED TABLE
-- ==========================
INSERT INTO unified_data (
    department_name,
    plc_name,
    resource_number,
    variable_name_id,
    KKS,
    comment,
    second_comment,
    variable_type,
    variable_value
)
VALUES
    -- Variables for Sidgal_1 Production Line
    ('Sidgal', 'S1E', '1', 'G00001', 'House.Output.KKS1', 'None', 'None', 'LINT', 123.45),
    ('Sidgal', 'S1E', '2', 'G00002', 'House.Output.KKS2', 'None', 'None', 'LINT', 678.90),
    ('Sidgal', 'S1C', '3', 'G00003', 'House.Output.KKS3', 'Maintenance Required', 'None', 'BOOL', 1),
    ('Sidgal', 'S1K', '4', 'G00004', 'House.Output.KKS4', 'None', 'Critical Issue', 'LINT', 0),

    -- Resources without variables in Sidgal_2 Production Line
    ('Sidgal', 'S2E', '1', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'S2C', '3', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'S2K', '2', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'S2S', '4', NULL, NULL, NULL, NULL, NULL, NULL),

    -- Variables for Sidgal_3 Production Line
    ('Sidgal', 'S3E', '1', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'S3C', '2', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'S3K', '3', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'S3S', '4', NULL, NULL, NULL, NULL, NULL, NULL),

    -- BT2: Only NIET, KMOR, and WT1 resource_numbers
    ('BT2', 'BTEST', 'NIET', 'BT2001', 'BT2.Output.KKS1', 'Example for NIET', 'Second Comment 1', 'LINT', 50.55),
    ('BT2', 'BTEST', 'KMOR', 'BT2002', 'BT2.Output.KKS2', 'Example for KMOR', 'Second Comment 2', 'BOOL', 1),
    ('BT2', 'BTEST', 'WT1', 'BT2003', 'BT2.Output.KKS3', 'Example for WT1', 'Second Comment 3', 'DOUBLE', 101.2);

-- ==========================
-- SELECT QUERY (ADJUSTED)
-- ==========================
SELECT *
FROM unified_data
WHERE department_name = 'BT2';