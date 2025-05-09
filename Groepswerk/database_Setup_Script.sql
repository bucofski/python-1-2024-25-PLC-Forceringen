-- ==========================
-- CREATE UNIFIED TABLE
-- ==========================
CREATE TABLE unified_data (
    department_name VARCHAR(255) NOT NULL,    -- E.g., Sidgal
    production_line_name VARCHAR(255) NOT NULL, -- E.g., Sidgal_1
    plc_name VARCHAR(255) NOT NULL,           -- E.g., S1E
    resource_number INT NOT NULL,             -- Resource number (e.g., 1 to 4)
    full_resource_name VARCHAR(255) NOT NULL, -- E.g., S1E1
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
    production_line_name,
    plc_name,
    resource_number,
    full_resource_name,
    variable_name_id,
    KKS,
    comment,
    second_comment,
    variable_type,
    variable_value
)
VALUES
    -- Variables for Sidgal_1 Production Line
    ('Sidgal', 'Sidgal_1', 'S1E', 1, 'S1E1', 'G00001', 'House.Output.KKS1', 'None', 'None', 'LINT', 123.45),
    ('Sidgal', 'Sidgal_1', 'S1E', 2, 'S1E2', 'G00002', 'House.Output.KKS2', 'None', 'None', 'LINT', 678.90),
    ('Sidgal', 'Sidgal_1', 'S1C', 1, 'S1C1', 'G00003', 'House.Output.KKS3', 'Maintenance Required', 'None', 'BOOL', 1),
    ('Sidgal', 'Sidgal_1', 'S1K', 3, 'S1K3', 'G00004', 'House.Output.KKS4', 'None', 'Critical Issue', 'LINT', 0),

    -- Resources without variables in Sidgal_1 Production Line
    ('Sidgal', 'Sidgal_1', 'S1K', 4, 'S1K4', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_1', 'S1S', 1, 'S1S1', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_1', 'S1S', 2, 'S1S2', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_1', 'S1S', 3, 'S1S3', NULL, NULL, NULL, NULL, NULL, NULL),

    -- Variables for Sidgal_2 Production Line
    ('Sidgal', 'Sidgal_2', 'S2E', 1, 'S2E1', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_2', 'S2C', 3, 'S2C3', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_2', 'S2K', 2, 'S2K2', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_2', 'S2S', 4, 'S2S4', NULL, NULL, NULL, NULL, NULL, NULL),

    -- Variables for Sidgal_3 Production Line
    ('Sidgal', 'Sidgal_3', 'S3E', 1, 'S3E1', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_3', 'S3C', 2, 'S3C2', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_3', 'S3K', 3, 'S3K3', NULL, NULL, NULL, NULL, NULL, NULL),
    ('Sidgal', 'Sidgal_3', 'S3S', 4, 'S3S4', NULL, NULL, NULL, NULL, NULL, NULL);

     SELECT *
     FROM unified_data
     WHERE production_line_name = 'Sidgal_1';
