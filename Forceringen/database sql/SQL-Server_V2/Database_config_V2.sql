-- Drop tables in correct order for SQL Server
IF OBJECT_ID('bit_force_reason', 'U') IS NOT NULL DROP TABLE bit_force_reason;
IF OBJECT_ID('resource_bit', 'U') IS NOT NULL DROP TABLE resource_bit;
IF OBJECT_ID('resource', 'U') IS NOT NULL DROP TABLE resource;
IF OBJECT_ID('bit', 'U') IS NOT NULL DROP TABLE bit; -- Fixed: was dropping 'resource' instead of 'bit'
IF OBJECT_ID('plc', 'U') IS NOT NULL DROP TABLE plc;

-- PLC table: each PLC is unique
CREATE TABLE plc (
    plc_id INT IDENTITY(1,1) PRIMARY KEY,
    plc_name NVARCHAR(100) NOT NULL UNIQUE
);

-- Resource table: resources can be shared among PLCs
CREATE TABLE resource (
    resource_id INT IDENTITY(1,1) PRIMARY KEY,
    resource_name NVARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE bit (
    bit_id INT IDENTITY(1,1) PRIMARY KEY,
    bit_number NVARCHAR(20) NOT NULL UNIQUE
); -- Fixed: removed trailing comma

-- Bit entries: now linked to BOTH plc and resource
CREATE TABLE resource_bit (
    resource_bit_id INT IDENTITY(1,1) PRIMARY KEY, -- Added primary key for this table
    bit_id INT NOT NULL REFERENCES bit(bit_id) ON DELETE CASCADE, -- Fixed: proper foreign key reference
    plc_id INT NOT NULL REFERENCES plc(plc_id) ON DELETE CASCADE,
    resource_id INT NOT NULL REFERENCES resource(resource_id) ON DELETE CASCADE,
    kks NVARCHAR(200),
    var_type NVARCHAR(6),
    comment NVARCHAR(MAX),
    second_comment NVARCHAR(MAX),
    force_active BIT DEFAULT 0,

    -- Combined uniqueness constraint: each combination of plc+resource+bit_number must be unique
    CONSTRAINT UQ_resource_bit_combination UNIQUE (plc_id, resource_id, bit_id)
);

-- Forced reasons
CREATE TABLE bit_force_reason (
    force_id INT IDENTITY(1,1) PRIMARY KEY,
    resource_bit_id INT NOT NULL REFERENCES resource_bit(resource_bit_id) ON DELETE CASCADE, -- Fixed: reference to correct table/column
    value NVARCHAR(50),
    reason NVARCHAR(MAX),
    melding NVARCHAR(100),
    forced_by NVARCHAR(100),
    forced_at DATETIMEOFFSET DEFAULT GETDATE(),
    deforced_at DATETIMEOFFSET NULL
);