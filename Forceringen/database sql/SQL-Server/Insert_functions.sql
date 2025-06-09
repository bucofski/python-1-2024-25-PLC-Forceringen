-- =============================================
-- function 4.0 change loggings - SQL Server version
-- =============================================
DROP PROCEDURE IF EXISTS upsert_plc_bits;

CREATE   PROCEDURE upsert_plc_bits
    @p_plc_name NVARCHAR(100),
    @p_resource_name NVARCHAR(100),
    @p_bits_data NVARCHAR(MAX)  -- JSON string instead of JSONB
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @v_plc_id INT;
    DECLARE @v_resource_id INT;
    DECLARE @v_bits_count INT = 0;
    DECLARE @v_error_msg NVARCHAR(MAX);
    DECLARE @v_bit_id INT;
    DECLARE @v_existing_force_status BIT;
    DECLARE @v_is_empty_json BIT = 0;
    DECLARE @v_json_array_length INT;

    -- Temporary table for incoming bit numbers
    CREATE TABLE #incoming_bit_numbers (bit_number NVARCHAR(20));

    -- Result table for return values
    CREATE TABLE #result (
        success BIT,
        message NVARCHAR(MAX),
        bits_processed INT
    );

    BEGIN TRY
        BEGIN TRANSACTION;

        -- 1. Ensure PLC exists
        IF NOT EXISTS (SELECT 1 FROM plc WHERE plc_name = @p_plc_name)
        BEGIN
            INSERT INTO plc (plc_name) VALUES (@p_plc_name);
        END

        SELECT @v_plc_id = plc_id FROM plc WHERE plc_name = @p_plc_name;

        IF @v_plc_id IS NULL
        BEGIN
            INSERT INTO #result VALUES (0, 'Failed to create/find PLC: ' + @p_plc_name, 0);
            SELECT * FROM #result;
            ROLLBACK TRANSACTION;
            RETURN;
        END

        -- 2. Ensure Resource exists
        IF NOT EXISTS (SELECT 1 FROM resource WHERE resource_name = @p_resource_name)
        BEGIN
            INSERT INTO resource (resource_name) VALUES (@p_resource_name);
        END

        SELECT @v_resource_id = resource_id FROM resource WHERE resource_name = @p_resource_name;

        IF @v_resource_id IS NULL
        BEGIN
            INSERT INTO #result VALUES (0, 'Failed to create/find Resource: ' + @p_resource_name, 0);
            SELECT * FROM #result;
            ROLLBACK TRANSACTION;
            RETURN;
        END

        -- 3. Check if JSON array is empty or null
        IF @p_bits_data IS NULL OR @p_bits_data = '' OR @p_bits_data = '[]'
        BEGIN
            SET @v_is_empty_json = 1;

            -- Update bit_force_reason for all bits that will be deactivated
            UPDATE bit_force_reason
            SET deforced_at = GETDATE()
            WHERE bit_id IN (
                SELECT bit_id FROM resource_bit
                WHERE plc_id = @v_plc_id
                AND resource_id = @v_resource_id
                AND force_active = 1
            ) AND deforced_at IS NULL;

            -- Deactivate ALL bits for this PLC/resource combination
            UPDATE resource_bit
            SET force_active = 0
            WHERE plc_id = @v_plc_id
            AND resource_id = @v_resource_id
            AND force_active = 1;

            COMMIT TRANSACTION;  -- Commit the changes before returning

            INSERT INTO #result VALUES (1, 'Empty JSON received - all bits set to force_active = FALSE for ' + @p_plc_name + '/' + @p_resource_name, 0);
            SELECT * FROM #result;
            RETURN;
        END

        -- 4. Extract all bit_numbers from the incoming JSON array
        INSERT INTO #incoming_bit_numbers (bit_number)
        SELECT name_id
        FROM OPENJSON(@p_bits_data)
        WITH (name_id NVARCHAR(20) '$.name_id')
        WHERE name_id IS NOT NULL;

        -- 5. Update bit_force_reason for bits that will be deactivated
        UPDATE bit_force_reason
        SET deforced_at = GETDATE()
        WHERE bit_id IN (
            SELECT rb.bit_id
            FROM resource_bit rb
            LEFT JOIN #incoming_bit_numbers ibn ON rb.bit_number = ibn.bit_number
            WHERE rb.plc_id = @v_plc_id
            AND rb.resource_id = @v_resource_id
            AND rb.force_active = 1
            AND ibn.bit_number IS NULL
        ) AND deforced_at IS NULL;

        -- 6. Deactivate bits that are NOT in the incoming array
        UPDATE resource_bit
        SET force_active = 0
     WHERE plc_id = @v_plc_id
        AND resource_id = @v_resource_id
        AND force_active = 1
        AND bit_number NOT IN (SELECT bit_number FROM #incoming_bit_numbers);

        -- 7. Process each bit in the JSON array using cursor
        DECLARE bit_cursor CURSOR FOR
        SELECT name_id, KKS, VAR_Type, Comment, Second_comment, [Value]
        FROM OPENJSON(@p_bits_data)
        WITH (
            name_id NVARCHAR(20) '$.name_id',
            KKS NVARCHAR(200) '$.KKS',
            VAR_Type NVARCHAR(6) '$.VAR_Type',
            Comment NVARCHAR(MAX) '$.Comment',
            Second_comment NVARCHAR(MAX) '$.Second_comment',
            [Value] NVARCHAR(50) '$.Value'
        );

        DECLARE @name_id NVARCHAR(20), @KKS NVARCHAR(200), @VAR_Type NVARCHAR(6),
                @Comment NVARCHAR(MAX), @Second_comment NVARCHAR(MAX), @Value NVARCHAR(50);

        OPEN bit_cursor;
        FETCH NEXT FROM bit_cursor INTO @name_id, @KKS, @VAR_Type, @Comment, @Second_comment, @Value;

        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Check existing force_active status
            SELECT @v_existing_force_status = force_active
            FROM resource_bit
            WHERE plc_id = @v_plc_id
            AND resource_id = @v_resource_id
            AND bit_number = @name_id;

            -- Merge operation (insert or update)
            MERGE resource_bit AS target
            USING (SELECT @v_plc_id AS plc_id, @v_resource_id AS resource_id, @name_id AS bit_number) AS source
            ON target.plc_id = source.plc_id
               AND target.resource_id = source.resource_id
               AND target.bit_number = source.bit_number
            WHEN MATCHED THEN
                UPDATE SET
                    kks = @KKS,
                    var_type = @VAR_Type,
                    comment = @Comment,
                    second_comment = @Second_comment,
                    value = @Value,
                    force_active = 1
            WHEN NOT MATCHED THEN
                INSERT (plc_id, resource_id, bit_number, kks, var_type, comment, second_comment, value, force_active)
                VALUES (@v_plc_id, @v_resource_id, @name_id, @KKS, @VAR_Type, @Comment, @Second_comment, @Value, 1);

            -- Get the bit_id
            SELECT @v_bit_id = bit_id
            FROM resource_bit
            WHERE plc_id = @v_plc_id
            AND resource_id = @v_resource_id
            AND bit_number = @name_id;

            -- Create new force reason entry if bit was inactive or didn't exist
            IF @v_existing_force_status IS NULL OR @v_existing_force_status = 0
            BEGIN
                INSERT INTO bit_force_reason (bit_id, forced_at)
                VALUES (@v_bit_id, GETDATE());
            END

            SET @v_bits_count = @v_bits_count + 1;
            FETCH NEXT FROM bit_cursor INTO @name_id, @KKS, @VAR_Type, @Comment, @Second_comment, @Value;
        END

        CLOSE bit_cursor;
        DEALLOCATE bit_cursor;

        COMMIT TRANSACTION;

        -- Success
        INSERT INTO #result VALUES (1, 'Successfully processed ' + CAST(@v_bits_count AS NVARCHAR(10)) + ' bits for ' + @p_plc_name + '/' + @p_resource_name, @v_bits_count);

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        SET @v_error_msg = ERROR_MESSAGE();
        INSERT INTO #result VALUES (0, 'Error: ' + @v_error_msg, @v_bits_count);
    END CATCH

    SELECT * FROM #result;

    DROP TABLE #incoming_bit_numbers;
    DROP TABLE #result;
END;
GO

-- =============================================
-- function 4.0 add reason - SQL Server version
-- =============================================

CREATE   PROCEDURE insert_force_reason
    @in_plc_name NVARCHAR(100),
    @in_resource_name NVARCHAR(100),
    @in_bit_number NVARCHAR(20),
    @in_reason NVARCHAR(MAX),
    @in_forced_by NVARCHAR(100) = 'UI User'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @v_bit_id INT;
    DECLARE @v_force_id INT;
    DECLARE @v_rows_updated INT;

    -- Result table
    CREATE TABLE #result (
        success BIT,
        message NVARCHAR(MAX)
    );

    -- Find the matching bit_id
    SELECT @v_bit_id = rb.bit_id
    FROM resource_bit rb
    INNER JOIN plc p ON rb.plc_id = p.plc_id
    INNER JOIN resource r ON rb.resource_id = r.resource_id
    WHERE p.plc_name = @in_plc_name
      AND r.resource_name = @in_resource_name
      AND rb.bit_number = @in_bit_number;

    -- Check if bit was found
    IF @v_bit_id IS NULL
    BEGIN
        INSERT INTO #result VALUES (0, 'Bit not found for PLC ' + @in_plc_name + ', Resource ' + @in_resource_name + ', Bit ' + @in_bit_number);
        SELECT * FROM #result;
        DROP TABLE #result;
        RETURN;
    END

    -- Find the latest force_id for this bit
    SELECT TOP 1 @v_force_id = force_id
    FROM bit_force_reason
    WHERE bit_id = @v_bit_id
      AND deforced_at IS NULL
    ORDER BY forced_at DESC;

    -- If no active force reason exists, create a new one
    IF @v_force_id IS NULL
    BEGIN
        INSERT INTO bit_force_reason (bit_id, reason, forced_by, forced_at)
        VALUES (@v_bit_id, @in_reason, @in_forced_by, GETDATE());

        INSERT INTO #result VALUES (1, 'New force reason created for PLC ' + @in_plc_name + ', Resource ' + @in_resource_name + ', Bit ' + @in_bit_number);
    END
    ELSE
    BEGIN
        -- Update the existing latest force reason entry
        UPDATE bit_force_reason
        SET reason = @in_reason,
            forced_by = @in_forced_by
        WHERE force_id = @v_force_id;

        SET @v_rows_updated = @@ROWCOUNT;

        IF @v_rows_updated > 0
        BEGIN
            INSERT INTO #result VALUES (1, 'Force reason updated for PLC ' + @in_plc_name + ', Resource ' + @in_resource_name + ', Bit ' + @in_bit_number);
        END
        ELSE
        BEGIN
            INSERT INTO #result VALUES (0, 'Failed to update force reason for PLC ' + @in_plc_name + ', Resource ' + @in_resource_name + ', Bit ' + @in_bit_number);
        END
    END

    -- Set force_active = TRUE if not already active
    UPDATE resource_bit
    SET force_active = 1
    WHERE bit_id = @v_bit_id AND force_active = 0;

    SELECT * FROM #result;
    DROP TABLE #result;
END;