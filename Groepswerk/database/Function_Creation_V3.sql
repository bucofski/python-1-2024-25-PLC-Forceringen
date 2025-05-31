-- =============================================
-- function 4.0 change loggings
-- =============================================

CREATE OR REPLACE FUNCTION upsert_plc_bits(
    p_plc_name TEXT,
    p_resource_name TEXT,
    p_bits_data JSONB  -- Array of bit objects
) RETURNS TABLE(
    success BOOLEAN,
    message TEXT,
    bits_processed INTEGER
) AS $$
DECLARE
    v_plc_id INTEGER;
    v_resource_id INTEGER;
    v_bit_record JSONB;
    v_bits_count INTEGER := 0;
    v_error_msg TEXT;
    v_incoming_bit_numbers TEXT[];
    v_bit_id INTEGER;
    v_existing_force_status BOOLEAN;
BEGIN
    -- Start transaction
    BEGIN
        -- 1. Ensure PLC exists (using correct column name: plc_name)
        INSERT INTO plc (plc_name) 
        VALUES (p_plc_name) 
        ON CONFLICT (plc_name) DO NOTHING;
        
        SELECT plc_id INTO v_plc_id FROM plc WHERE plc_name = p_plc_name;
        
        IF v_plc_id IS NULL THEN
            RETURN QUERY SELECT FALSE::BOOLEAN, 'Failed to create/find PLC: ' || p_plc_name, 0;
            RETURN;
        END IF;

        -- 2. Ensure Resource exists (using correct column name: resource_name)
        INSERT INTO resource (resource_name) 
        VALUES (p_resource_name) 
        ON CONFLICT (resource_name) DO NOTHING;
        
        SELECT resource_id INTO v_resource_id FROM resource 
        WHERE resource_name = p_resource_name;
        
        IF v_resource_id IS NULL THEN
            RETURN QUERY SELECT FALSE::BOOLEAN, 'Failed to create/find Resource: ' || p_resource_name, 0;
            RETURN;
        END IF;

        -- 3. Extract all bit_numbers from the incoming JSON array
        SELECT ARRAY(
            SELECT elem->>'name_id'
            FROM jsonb_array_elements(p_bits_data) AS elem
            WHERE elem->>'name_id' IS NOT NULL
        ) INTO v_incoming_bit_numbers;

        -- 4. Update bit_force_reason for bits that will be deactivated (not in incoming array)
        UPDATE bit_force_reason 
        SET deforced_at = NOW() 
        WHERE bit_id IN (
            SELECT bit_id FROM resource_bit 
            WHERE plc_id = v_plc_id 
            AND resource_id = v_resource_id 
            AND force_active = TRUE
            AND bit_number <> ALL(v_incoming_bit_numbers)
        ) AND deforced_at IS NULL;

        -- 5. Deactivate bits that are NOT in the incoming array
        UPDATE resource_bit 
        SET force_active = FALSE 
        WHERE plc_id = v_plc_id 
        AND resource_id = v_resource_id 
        AND force_active = TRUE
        AND bit_number <> ALL(v_incoming_bit_numbers);

        -- 6. Process each bit in the JSON array
        FOR v_bit_record IN SELECT jsonb_array_elements(p_bits_data)
        LOOP
            -- Check if bit exists and its current force_active status BEFORE insert/update
            SELECT force_active INTO v_existing_force_status
            FROM resource_bit 
            WHERE plc_id = v_plc_id 
            AND resource_id = v_resource_id 
            AND bit_number = v_bit_record->>'name_id';

            -- Insert/Update each bit (using correct column names)
            INSERT INTO resource_bit (
                plc_id, resource_id, bit_number, kks, VAR_Type, comment, second_comment,
                value, force_active
            ) VALUES (
                v_plc_id,
                v_resource_id,
                v_bit_record->>'name_id',  -- maps to bit_number
                v_bit_record->>'KKS',      -- maps to kks
				v_bit_record->>'VAR_Type', -- maps to Variable Type
                v_bit_record->>'Comment',  -- maps to comment
                v_bit_record->>'Second_comment', -- maps to second_comment
                v_bit_record->>'Value',    -- maps to value
                TRUE
            )
            ON CONFLICT (plc_id, resource_id, bit_number) DO UPDATE SET
                kks = EXCLUDED.kks,
				VAR_Type = EXCLUDED.VAR_Type,
                comment = EXCLUDED.comment,
                second_comment = EXCLUDED.second_comment,
                value = EXCLUDED.value,
                force_active = TRUE
            RETURNING bit_id INTO v_bit_id;

            -- Create new force reason entry if bit was inactive or didn't exist
            IF v_existing_force_status IS NULL OR v_existing_force_status = FALSE THEN
                INSERT INTO bit_force_reason (
                    bit_id,
                    forced_at
                ) VALUES (
                    v_bit_id,
                    NOW()
                );
            END IF;

            v_bits_count := v_bits_count + 1;
        END LOOP;

        -- Success
        RETURN QUERY SELECT
            TRUE::BOOLEAN,
            'Successfully processed ' || v_bits_count || ' bits for ' || p_plc_name || '/' || p_resource_name,
            v_bits_count;

    EXCEPTION WHEN OTHERS THEN
        -- Handle any errors
        GET STACKED DIAGNOSTICS v_error_msg = MESSAGE_TEXT;
        RETURN QUERY SELECT
            FALSE::BOOLEAN,
            'Error: ' || v_error_msg,
            v_bits_count;
    END;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- function 4.0 add reason
-- =============================================

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
    v_force_id INTEGER;
    v_rows_updated INTEGER;
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

    -- Find the latest force_id for this bit (the most recent forced entry that hasn't been deforced)
    SELECT force_id INTO v_force_id
    FROM bit_force_reason
    WHERE bit_id = v_bit_id
      AND deforced_at IS NULL
    ORDER BY forced_at DESC
    LIMIT 1;

    -- If no active force reason exists, create a new one
    IF v_force_id IS NULL THEN
        INSERT INTO bit_force_reason (bit_id, reason, forced_by, forced_at)
        VALUES (v_bit_id, in_reason, in_forced_by())
        RETURNING force_id INTO v_force_id;
        
        RETURN QUERY SELECT TRUE AS success, 
                    format('New force reason created for PLC %s, Resource %s, Bit %s', 
                           in_plc_name, in_resource_name, in_bit_number) AS message;
    ELSE
        -- Update the existing latest force reason entry
        UPDATE bit_force_reason
        SET reason = in_reason,
            forced_by = in_forced_by
        WHERE force_id = v_force_id;
        
        GET DIAGNOSTICS v_rows_updated = ROW_COUNT;
        
        IF v_rows_updated > 0 THEN
            RETURN QUERY SELECT TRUE AS success, 
                        format('Force reason updated for PLC %s, Resource %s, Bit %s', 
                               in_plc_name, in_resource_name, in_bit_number) AS message;
        ELSE
            RETURN QUERY SELECT FALSE AS success, 
                        format('Failed to update force reason for PLC %s, Resource %s, Bit %s', 
                               in_plc_name, in_resource_name, in_bit_number) AS message;
        END IF;
    END IF;

    -- Set force_active = TRUE if not already active
    UPDATE resource_bit
    SET force_active = TRUE
    WHERE bit_id = v_bit_id AND force_active = FALSE;
    
END;
$$ LANGUAGE plpgsql;

