
-- =============================================
-- function 3.0
-- =============================================

CREATE OR REPLACE FUNCTION upsert_plc_bits(
    p_plc_name TEXT,
    p_resource_name TEXT,
    p_bits_data JSONB
) RETURNS TABLE(
    success BOOLEAN,
    message TEXT,
    bits_processed INTEGER
) AS $$
DECLARE
    v_plc_id INTEGER;
    v_resource_id INTEGER;
    v_error_msg TEXT;
    v_bits_count INTEGER := 0;
BEGIN
    BEGIN
        -- 1. Ensure PLC exists
        INSERT INTO plc (plc_name) 
        VALUES (p_plc_name) 
        ON CONFLICT (plc_name) DO NOTHING;

        SELECT plc_id INTO v_plc_id FROM plc WHERE plc_name = p_plc_name;
        IF v_plc_id IS NULL THEN
            RETURN QUERY SELECT FALSE, 'Failed to resolve PLC', 0;
            RETURN;
        END IF;

        -- 2. Ensure Resource exists
        INSERT INTO resource (resource_name) 
        VALUES (p_resource_name) 
        ON CONFLICT (resource_name) DO NOTHING;

        SELECT resource_id INTO v_resource_id FROM resource WHERE resource_name = p_resource_name;
        IF v_resource_id IS NULL THEN
            RETURN QUERY SELECT FALSE, 'Failed to resolve Resource', 0;
            RETURN;
        END IF;

        -- 3. Deactivate only bits NOT in incoming list
        UPDATE resource_bit rb
        SET 
            force_active = FALSE,
            deforced_at = NOW()
        WHERE rb.plc_id = v_plc_id
          AND rb.resource_id = v_resource_id
          AND rb.force_active = TRUE
          AND NOT EXISTS (
              SELECT 1
              FROM jsonb_array_elements(p_bits_data) AS elem
              WHERE elem->>'name_id' = rb.bit_number
          );

        -- 4. Create temp table for incoming data
        CREATE TEMP TABLE temp_bits (
            bit_number TEXT,
            kks TEXT,
            comment TEXT,
            second_comment TEXT,
            value TEXT
        ) ON COMMIT DROP;

        -- 5. Populate temp table
        INSERT INTO temp_bits (bit_number, kks, comment, second_comment, value)
        SELECT 
            elem->>'name_id',
            elem->>'KKS',
            elem->>'Comment',
            elem->>'Second_comment',
            elem->>'Value'
        FROM jsonb_array_elements(p_bits_data) elem;

        -- 6. Insert new records (not existing yet)
        INSERT INTO resource_bit (
            plc_id, resource_id, bit_number, kks, comment, second_comment,
            value, force_active, forced_at, deforced_at
        )
        SELECT 
            v_plc_id, v_resource_id, tb.bit_number, tb.kks, tb.comment, tb.second_comment,
            tb.value, TRUE, NOW(), NULL
        FROM temp_bits tb
        LEFT JOIN resource_bit rb
          ON rb.plc_id = v_plc_id AND rb.resource_id = v_resource_id AND rb.bit_number = tb.bit_number
        WHERE rb.bit_number IS NULL;

        -- 7. Update existing bits
        UPDATE resource_bit rb
        SET
            kks = tb.kks,
            comment = tb.comment,
            second_comment = tb.second_comment,
            value = tb.value,
            force_active = TRUE,
            forced_at = CASE
                WHEN rb.force_active = FALSE THEN NOW()
                ELSE rb.forced_at
            END,
            deforced_at = NULL  -- Clear deforced_at if reactivated
        FROM temp_bits tb
        WHERE rb.plc_id = v_plc_id
          AND rb.resource_id = v_resource_id
          AND rb.bit_number = tb.bit_number;

        -- 8. Count processed
        SELECT COUNT(*) INTO v_bits_count FROM temp_bits;

        -- 9. Return success
        RETURN QUERY SELECT
            TRUE,
            format('Successfully processed %s bits for %s/%s', v_bits_count, p_plc_name, p_resource_name),
            v_bits_count;

    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_error_msg = MESSAGE_TEXT;
        RETURN QUERY SELECT FALSE, 'Error: ' || v_error_msg, v_bits_count;
    END;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- function 3.0 add reason
-- =============================================

-- Procedure to add force reasons for bits

CREATE OR REPLACE FUNCTION insert_force_reason(
    in_plc_name VARCHAR,
    in_resource_name VARCHAR,
    in_bit_number VARCHAR,
    in_reason TEXT,
    in_forced_by VARCHAR DEFAULT 'UI User'  -- Default value added
) RETURNS TABLE (
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    v_bit_id INTEGER;
BEGIN
    -- Find the matching bit_id
    SELECT rb.bit_id INTO v_bit_id
    FROM resource_bit rb
    JOIN plc p ON rb.plc_id = p.plc_id
    JOIN resource r ON rb.resource_id = r.resource_id
    WHERE p.plc_name = in_plc_name
      AND r.resource_name = in_resource_name
      AND rb.bit_number = in_bit_number;

    -- Check if bit was found
    IF v_bit_id IS NULL THEN
        RETURN QUERY SELECT FALSE AS success, 
                    format('Bit not found for PLC %s, Resource %s, Bit %s', 
                           in_plc_name, in_resource_name, in_bit_number) AS message;
        RETURN;
    END IF;

    -- Insert reason into bit_force_reason
    INSERT INTO bit_force_reason (bit_id, reason, forced_by)
    VALUES (v_bit_id, in_reason, in_forced_by);

    -- Set force_active = TRUE
    UPDATE resource_bit
    SET force_active = TRUE, forced_at = NOW()
    WHERE bit_id = v_bit_id;
    
    -- Return success
    RETURN QUERY SELECT TRUE AS success, 
                format('Reason saved successfully for PLC %s, Resource %s, Bit %s', 
                       in_plc_name, in_resource_name, in_bit_number) AS message;
END;
$$ LANGUAGE plpgsql;

select * from bit_force_reason
SELECT insert_force_reason('BTEST', 'NIET', 'I00000', 'Manual override for testing', 'tech_user1');