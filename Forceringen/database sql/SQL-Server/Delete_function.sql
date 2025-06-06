-- Function to delete bits for a specific PLC-resource combination only - SQL Server version
CREATE OR ALTER PROCEDURE delete_plc_resource_bits
    @p_plc_name NVARCHAR(100),
    @p_resource_name NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @v_plc_id INT;
    DECLARE @v_resource_id INT;
    DECLARE @v_deleted_bits INT = 0;
    DECLARE @v_deleted_reasons INT = 0;

    -- Result table
    CREATE TABLE #result (
        deleted_bits_count INT,
        deleted_force_reasons_count INT,
        message NVARCHAR(MAX)
    );

    -- Get the PLC and Resource IDs
    SELECT @v_plc_id = plc_id
    FROM plc
    WHERE plc_name = @p_plc_name;

    SELECT @v_resource_id = resource_id
    FROM resource
    WHERE resource_name = @p_resource_name;

    -- If either doesn't exist, return zeros
    IF @v_plc_id IS NULL
    BEGIN
        INSERT INTO #result VALUES (0, 0, 'PLC not found: ' + @p_plc_name);
        SELECT * FROM #result;
        DROP TABLE #result;
        RETURN;
    END

    IF @v_resource_id IS NULL
    BEGIN
        INSERT INTO #result VALUES (0, 0, 'Resource not found: ' + @p_resource_name);
        SELECT * FROM #result;
        DROP TABLE #result;
        RETURN;
    END

    -- Count force reasons that will be deleted
    SELECT @v_deleted_reasons = COUNT(*)
    FROM bit_force_reason bfr
    INNER JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
    WHERE rb.plc_id = @v_plc_id AND rb.resource_id = @v_resource_id;

    -- Count bits that will be deleted
    SELECT @v_deleted_bits = COUNT(*)
    FROM resource_bit
    WHERE plc_id = @v_plc_id AND resource_id = @v_resource_id;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Delete force reasons first (due to foreign key constraints)
        DELETE bfr
        FROM bit_force_reason bfr
        INNER JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
        WHERE rb.plc_id = @v_plc_id AND rb.resource_id = @v_resource_id;

        -- Delete all bits for this specific PLC-resource combination
        DELETE FROM resource_bit
        WHERE plc_id = @v_plc_id AND resource_id = @v_resource_id;

        COMMIT TRANSACTION;

        -- Return counts and success message
        INSERT INTO #result VALUES (
            @v_deleted_bits,
            @v_deleted_reasons,
            'Deleted ' + CAST(@v_deleted_bits AS NVARCHAR(10)) + ' bits and ' +
            CAST(@v_deleted_reasons AS NVARCHAR(10)) + ' force reasons for PLC ' +
            @p_plc_name + ', Resource ' + @p_resource_name
        );

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        INSERT INTO #result VALUES (0, 0, 'Error deleting data: ' + ERROR_MESSAGE());
    END CATCH

    SELECT * FROM #result;
    DROP TABLE #result;
END;
GO

-- Test the procedure
EXEC delete_plc_resource_bits @p_plc_name = 'AFV', @p_resource_name = 'House';
GO

-- Function to delete entire PLC and all associated data - SQL Server version
CREATE OR ALTER PROCEDURE delete_plc_all_bits
    @p_plc_name NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @v_plc_id INT;
    DECLARE @v_deleted_bits INT = 0;
    DECLARE @v_deleted_reasons INT = 0;

    -- Result table
    CREATE TABLE #result (
        deleted_plc_count INT,
        deleted_bits_count INT,
        deleted_force_reasons_count INT,
        message NVARCHAR(MAX)
    );

    -- Get the PLC ID
    SELECT @v_plc_id = plc_id
    FROM plc
    WHERE plc_name = @p_plc_name;

    -- If PLC doesn't exist, return zeros
    IF @v_plc_id IS NULL
    BEGIN
        INSERT INTO #result VALUES (0, 0, 0, 'PLC not found: ' + @p_plc_name);
        SELECT * FROM #result;
        DROP TABLE #result;
        RETURN;
    END

    -- Count force reasons that will be deleted
    SELECT @v_deleted_reasons = COUNT(*)
    FROM bit_force_reason bfr
    INNER JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
    WHERE rb.plc_id = @v_plc_id;

    -- Count bits that will be deleted
    SELECT @v_deleted_bits = COUNT(*)
    FROM resource_bit
    WHERE plc_id = @v_plc_id;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Delete force reasons first (due to foreign key constraints)
        DELETE bfr
        FROM bit_force_reason bfr
        INNER JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
        WHERE rb.plc_id = @v_plc_id;

        -- Delete all bits for this PLC
        DELETE FROM resource_bit
        WHERE plc_id = @v_plc_id;

        -- Delete the PLC
        DELETE FROM plc WHERE plc_id = @v_plc_id;

        COMMIT TRANSACTION;

        -- Return counts and success message
        INSERT INTO #result VALUES (
            1,
            @v_deleted_bits,
            @v_deleted_reasons,
            'Deleted PLC ' + @p_plc_name + ' with ' + CAST(@v_deleted_bits AS NVARCHAR(10)) +
            ' bits and ' + CAST(@v_deleted_reasons AS NVARCHAR(10)) + ' force reasons across all resources'
        );

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        INSERT INTO #result VALUES (0, 0, 0, 'Error deleting PLC: ' + ERROR_MESSAGE());
    END CATCH

    SELECT * FROM #result;
    DROP TABLE #result;
END;
GO

-- Test the procedure
EXEC delete_plc_all_bits @p_plc_name = 'AFV';
GO