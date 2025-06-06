
-- Drop tables in correct order for SQL Server
IF OBJECT_ID('bit_force_reason', 'U') IS NOT NULL DROP TABLE bit_force_reason;
IF OBJECT_ID('resource_bit', 'U') IS NOT NULL DROP TABLE resource_bit;
IF OBJECT_ID('resource', 'U') IS NOT NULL DROP TABLE resource;
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

-- Bit entries: now linked to BOTH plc and resource
CREATE TABLE resource_bit (
    bit_id INT IDENTITY(1,1) PRIMARY KEY,
    plc_id INT NOT NULL REFERENCES plc(plc_id) ON DELETE CASCADE,
    resource_id INT NOT NULL REFERENCES resource(resource_id) ON DELETE CASCADE,
    bit_number NVARCHAR(20) NOT NULL,
    kks NVARCHAR(200),
    var_type NVARCHAR(6),
    comment NVARCHAR(MAX),
    second_comment NVARCHAR(MAX),
    value NVARCHAR(50),
    force_active BIT DEFAULT 0,

    -- uniqueness now guarantees each plc+resource has unique bit
    UNIQUE (plc_id, resource_id, bit_number)
);

-- Forced reasons
CREATE TABLE bit_force_reason (
    force_id INT IDENTITY(1,1) PRIMARY KEY,
    bit_id INT NOT NULL REFERENCES resource_bit(bit_id) ON DELETE CASCADE,
    reason NVARCHAR(MAX),
    forced_by NVARCHAR(100),
    forced_at DATETIMEOFFSET DEFAULT GETDATE(),
    deforced_at DATETIMEOFFSET NULL
);