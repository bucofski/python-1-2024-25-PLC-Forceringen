-- ==========================
-- TABLE CREATION
-- ==========================

-- 1. Create the 'departments' table
CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,  -- Unique identifier for each department
    name VARCHAR(255) NOT NULL UNIQUE  -- Name of the department (unique)
);

-- 2. Create the 'production_lines' table
CREATE TABLE production_lines (
    production_line_id SERIAL PRIMARY KEY,  -- Unique identifier for each production line
    department_id INT NOT NULL,            -- Foreign key to 'departments'
    name VARCHAR(255) NOT NULL,            -- Name of the production line
    UNIQUE(department_id, name),           -- Combination of department and name is unique
    FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE CASCADE
);

-- 3. Create the 'plcs' table
CREATE TABLE plcs (
    plc_id SERIAL PRIMARY KEY,             -- Unique identifier for each PLC
    production_line_id INT NOT NULL,       -- Foreign key to 'production_lines'
    name VARCHAR(255) NOT NULL,            -- Name or identifier of the PLC
    UNIQUE(production_line_id, name),      -- PLC names are unique within a production line
    FOREIGN KEY (production_line_id) REFERENCES production_lines(production_line_id) ON DELETE CASCADE
);

-- 4. Create the 'resources' table
CREATE TABLE resources (
    resource_id SERIAL PRIMARY KEY,        -- Unique identifier for each resource
    plc_id INT NOT NULL,                   -- Foreign key to 'plcs'
    name VARCHAR(255) NOT NULL,            -- Name or identifier of the resource
    UNIQUE(plc_id, name),                  -- Resource names are unique within a PLC
    FOREIGN KEY (plc_id) REFERENCES plcs(plc_id) ON DELETE CASCADE
);

-- 5. Create the 'variables' table
CREATE TABLE variables (
    variable_id SERIAL PRIMARY KEY,        -- Unique identifier for each variable
    resource_id INT NOT NULL,              -- Foreign key to 'resources'
    name_id VARCHAR(255) NOT NULL,         -- Name identifier (e.g., G00000)
    KKS VARCHAR(255) NOT NULL,             -- KKS identifier
    comment TEXT,                          -- Comment associated with the variable
    second_comment TEXT,                   -- Secondary comment associated with the variable
    type VARCHAR(50) NOT NULL,             -- Data type (e.g., LINT)
    value DOUBLE PRECISION NOT NULL,       -- Value of the variable
    UNIQUE(resource_id, name_id),          -- Variables are unique within a resource
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE CASCADE
);

-- ==========================
-- SAMPLE DATA INSERTION
-- ==========================

-- Add department
INSERT INTO departments (name)
VALUES
    ('Sidgal');

-- Add production lines for department 'Sidgal' (id = 1)
INSERT INTO production_lines (department_id, name)
VALUES
    (1, 'Sidgal_1'),
    (1, 'Sidgal_2'),
    (1, 'Sidgal_3');


-- Add PLCs for all production lines (Sidgal_1, Sidgal_2, Sidgal_3)
INSERT INTO plcs (production_line_id, name)
VALUES
    -- PLCs for Sidgal_1 (production_line_id = 1)
    (1, 'S1E'), (1, 'S1C'), (1, 'S1K'), (1, 'S1S'),
    -- PLCs for Sidgal_2 (production_line_id = 2)
    (2, 'S2E'), (2, 'S2C'), (2, 'S2K'), (2, 'S2S'),
    -- PLCs for Sidgal_3 (production_line_id = 3)
    (3, 'S3E'), (3, 'S3C'), (3, 'S3K'), (3, 'S3S');

-- Add resources for all PLCs
INSERT INTO resources (plc_id, name)
VALUES
    -- Resources for PLCs under Sidgal_1
    (1, 'E1'), (1, 'E2'), (1, 'E3'), (1, 'E4'),    -- For S1E (plc_id = 1)
    (2, 'C1'), (2, 'C2'), (2, 'C3'), (2, 'C4'),    -- For S1C (plc_id = 2)
    (3, 'K1'), (3, 'K2'), (3, 'K3'), (3, 'K4'),    -- For S1K (plc_id = 3)
    (4, 'S1'), (4, 'S2'), (4, 'S3'), (4, 'S4'),    -- For S1S (plc_id = 4)

    -- Resources for PLCs under Sidgal_2
    (5, 'E1'), (5, 'E2'), (5, 'E3'), (5, 'E4'),    -- For S2E (plc_id = 5)
    (6, 'C1'), (6, 'C2'), (6, 'C3'), (6, 'C4'),    -- For S2C (plc_id = 6)
    (7, 'K1'), (7, 'K2'), (7, 'K3'), (7, 'K4'),    -- For S2K (plc_id = 7)
    (8, 'S1'), (8, 'S2'), (8, 'S3'), (8, 'S4'),    -- For S2S (plc_id = 8)

    -- Resources for PLCs under Sidgal_3
    (9, 'E1'),  (9, 'E2'),  (9, 'E3'),  (9, 'E4'),  -- For S3E (plc_id = 9)
    (10, 'C1'), (10, 'C2'), (10, 'C3'), (10, 'C4'), -- For S3C (plc_id = 10)
    (11, 'K1'), (11, 'K2'), (11, 'K3'), (11, 'K4'), -- For S3K (plc_id = 11)
    (12, 'S1'), (12, 'S2'), (12, 'S3'), (12, 'S4'); -- For S3S (plc_id = 12)


-- Add Variables
INSERT INTO variables (resource_id, name_id, KKS, comment, second_comment, type, value) 
VALUES 
    (1, 'G00001', 'House.Output.KKS1', 'None', 'None', 'LINT', 123.45),
    (1, 'G00002', 'House.Output.KKS2', 'None', 'None', 'LINT', 678.90),
    (2, 'G00003', 'House.Output.KKS3', 'Maintenance Required', 'None', 'BOOL', 1),
    (3, 'G00004', 'House.Output.KKS4', 'None', 'Critical Issue', 'LINT', 0);