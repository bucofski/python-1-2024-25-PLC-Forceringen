-- Function to delete bits for a specific PLC-resource combination only
CREATE OR REPLACE FUNCTION delete_plc_resource_bits(
    p_plc_name VARCHAR,
    p_resource_name VARCHAR
)
RETURNS TABLE(
    deleted_bits_count INTEGER,
    deleted_force_reasons_count INTEGER,
    message TEXT
) AS $$
DECLARE
    v_plc_id INTEGER;
    v_resource_id INTEGER;
    v_deleted_bits INTEGER := 0;
    v_deleted_reasons INTEGER := 0;
BEGIN
    -- Get the PLC and Resource IDs
    SELECT plc_id INTO v_plc_id
    FROM plc
    WHERE plc_name = p_plc_name;

    SELECT resource_id INTO v_resource_id
    FROM resource
    WHERE resource_name = p_resource_name;

    -- If either doesn't exist, return zeros
    IF v_plc_id IS NULL THEN
        RETURN QUERY SELECT 0, 0, 'PLC not found: ' || p_plc_name;
        RETURN;
    END IF;

    IF v_resource_id IS NULL THEN
        RETURN QUERY SELECT 0, 0, 'Resource not found: ' || p_resource_name;
        RETURN;
    END IF;

    -- Count force reasons that will be deleted
    SELECT COUNT(*) INTO v_deleted_reasons
    FROM bit_force_reason bfr
    JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
    WHERE rb.plc_id = v_plc_id AND rb.resource_id = v_resource_id;

    -- Count bits that will be deleted
    SELECT COUNT(*) INTO v_deleted_bits
    FROM resource_bit
    WHERE plc_id = v_plc_id AND resource_id = v_resource_id;

    -- Delete all bits for this specific PLC-resource combination
    -- (CASCADE will automatically handle force reasons)
    DELETE FROM resource_bit
    WHERE plc_id = v_plc_id AND resource_id = v_resource_id;

    -- Return counts and success message
    RETURN QUERY SELECT
        v_deleted_bits,
        v_deleted_reasons,
        format('Deleted %s bits and %s force reasons for PLC %s, Resource %s',
               v_deleted_bits, v_deleted_reasons, p_plc_name, p_resource_name);
END;
$$ LANGUAGE plpgsql;


SELECT * FROM delete_plc_resource_bits('AFV', 'House');



-- Function to delete entire PLC and all associated data
CREATE OR REPLACE FUNCTION delete_plc_all_bits(
    p_plc_name VARCHAR
)
RETURNS TABLE(
    deleted_plc_count INTEGER,
    deleted_bits_count INTEGER,
    deleted_force_reasons_count INTEGER,
    message TEXT
) AS $$
DECLARE
    v_plc_id INTEGER;
    v_deleted_bits INTEGER := 0;
    v_deleted_reasons INTEGER := 0;
BEGIN
    -- Get the PLC ID
    SELECT plc_id INTO v_plc_id
    FROM plc
    WHERE plc_name = p_plc_name;

    -- If PLC doesn't exist, return zeros
    IF v_plc_id IS NULL THEN
        RETURN QUERY SELECT 0, 0, 0, 'PLC not found: ' || p_plc_name;
        RETURN;
    END IF;

    -- Count force reasons that will be deleted
    SELECT COUNT(*) INTO v_deleted_reasons
    FROM bit_force_reason bfr
    JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
    WHERE rb.plc_id = v_plc_id;

    -- Count bits that will be deleted
    SELECT COUNT(*) INTO v_deleted_bits
    FROM resource_bit
    WHERE plc_id = v_plc_id;

    -- Delete the PLC (CASCADE will handle all resource_bit and bit_force_reason records)
    DELETE FROM plc WHERE plc_id = v_plc_id;

    -- Return counts and success message
    RETURN QUERY SELECT
        1,
        v_deleted_bits,
        v_deleted_reasons,
        format('Deleted PLC %s with %s bits and %s force reasons across all resources',
               p_plc_name, v_deleted_bits, v_deleted_reasons);
END;
$$ LANGUAGE plpgsql;

SELECT * FROM delete_plc_all_bits('AFV');