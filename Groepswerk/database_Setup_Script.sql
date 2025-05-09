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

-- Add departments
INSERT INTO departments (name) 
VALUES 
    ('Manufacturing'), 
    ('Packaging');

-- Add production lines
INSERT INTO production_lines (department_id, name) 
VALUES 
    (1, 'Line1'), 
    (1, 'Line2'), 
    (2, 'LineA');

-- Add PLCs
INSERT INTO plcs (production_line_id, name) 
VALUES 
    (1, 'PLC1'), 
    (1, 'PLC2'), 
    (2, 'PLC3'), 
    (3, 'PLC4');

-- Add Resources
INSERT INTO resources (plc_id, name) 
VALUES 
    (1, 'Resource1'), 
    (1, 'Resource2'), 
    (2, 'Resource3'), 
    (3, 'Resource4');

-- Add Variables
INSERT INTO variables (resource_id, name_id, KKS, comment, second_comment, type, value) 
VALUES 
    (1, 'G00001', 'House.Output.KKS1', 'None', 'None', 'LINT', 123.45),
    (1, 'G00002', 'House.Output.KKS2', 'None', 'None', 'LINT', 678.90),
    (2, 'G00003', 'House.Output.KKS3', 'Maintenance Required', 'None', 'BOOL', 1),
    (3, 'G00004', 'House.Output.KKS4', 'None', 'Critical Issue', 'LINT', 0);