DROP TABLE IF EXISTS bit_force_reason, resource_bit, resource, plc CASCADE;

-- PLC table: each PLC is unique
CREATE TABLE plc (
    plc_id SERIAL PRIMARY KEY,
    plc_name VARCHAR(100) NOT NULL UNIQUE
);

-- Resource table: resources can be shared among PLCs
CREATE TABLE resource (
    resource_id SERIAL PRIMARY KEY,
    resource_name VARCHAR(100) NOT NULL UNIQUE
);

-- Bit entries: now linked to BOTH plc and resource
CREATE TABLE resource_bit (
    bit_id SERIAL PRIMARY KEY,
    plc_id INTEGER NOT NULL REFERENCES plc(plc_id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resource(resource_id) ON DELETE CASCADE,
    bit_number VARCHAR(20) NOT NULL,
    kks VARCHAR(200),
    comment TEXT,
    second_comment TEXT,
    value VARCHAR(50),
    force_active BOOLEAN DEFAULT FALSE,

    -- uniqueness now guarantees each plc+resource has unique bit
    UNIQUE (plc_id, resource_id, bit_number)
);

-- Forced reasons
CREATE TABLE bit_force_reason (
    force_id SERIAL PRIMARY KEY,
    bit_id INTEGER NOT NULL REFERENCES resource_bit(bit_id) ON DELETE CASCADE,
    reason TEXT,
    forced_by VARCHAR(100),
	forced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deforced_at TIMESTAMP WITH TIME ZONE NULL
);