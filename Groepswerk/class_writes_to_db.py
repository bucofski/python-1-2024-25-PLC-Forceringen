import psycopg2
# from class_bit_conversion import BitConversion
#
#
#
# class BitConversionDBWriter(BitConversion):
#     """
#     Inherits BitConversion. After conversion, writes entries to a database table.
#     Manages the 'active' column: sets active=True for given name_ids, and active=False for the rest (filtered by PLC and resource).
#     """
#
#     def __init__(self, data_list, db_conn, table_name):
#         super().__init__(data_list)
#         self.db_conn = db_conn
#         self.table_name = table_name
#
#     def write_to_database(self):
#         processed_list = self.convert_variable_list()
#
#         if not processed_list:
#             return
#
#         # Gather unique PLC and resource from the input list
#         plc = processed_list[0].get("PLC")
#         resource = processed_list[0].get("resource")
#         name_ids = [row["name_id"] for row in processed_list]
#
#         # Deactivate all for this PLC and resource
#         deactivate_sql = f"""
#             UPDATE {self.table_name}
#             SET active = FALSE
#             WHERE PLC = %s AND resource = %s
#         """
#
#         # Insert or update with active=True
#         upsert_sql = f"""
#             INSERT INTO {self.table_name}
#             (name_id, PLC, resource, KKS, Comment, Second_comment, VAR_Type, Value, department_name, active)
#             VALUES
#             (%(name_id)s, %(PLC)s, %(resource)s, %(KKS)s, %(Comment)s, %(Second_comment)s, %(VAR_Type)s, %(Value)s, %(department_name)s, TRUE)
#             ON CONFLICT (name_id) DO UPDATE SET
#                 PLC = EXCLUDED.PLC,
#                 resource = EXCLUDED.resource,
#                 KKS = EXCLUDED.KKS,
#                 Comment = EXCLUDED.Comment,
#                 Second_comment = EXCLUDED.Second_comment,
#                 VAR_Type = EXCLUDED.VAR_Type,
#                 Value = EXCLUDED.Value,
#                 department_name = EXCLUDED.department_name,
#                 active = TRUE
#         """
#
#         with self.db_conn:
#             with self.db_conn.cursor() as cur:
#                 # Set all to inactive first
#                 cur.execute(deactivate_sql, (plc, resource))
#                 # Upsert current records as active
#                 for row in processed_list:
#                     cur.execute(upsert_sql, row)


import psycopg2
from psycopg2 import sql
import yaml
from datetime import datetime


class BitDatabaseManager:
    """
    A class to manage bit entries in the database.
    Provides functionality to add, update, and query bits.
    """

    def __init__(self, db_connection_params):
        """
        Initialize with database connection parameters.

        Parameters:
        - db_connection_params: dict with keys 'host', 'database', 'user', 'password', 'port'
        """
        self.conn_params = db_connection_params
        self.conn = None

    def connect(self):
        """Establish a connection to the database."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.conn_params)
        return self.conn

    def close(self):
        """Close the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def add_bit(self, resource_name, bit_number, kks, comment=None, second_comment=None, value=None, forced_by=None,
                reason=None):
        """
        Add a new bit to the resource_bit table or update if it already exists.
        All added or updated bits will have force_Active set to True.
        Also records the forcing reason if provided.

        Parameters:
        - resource_name: The name of the resource
        - bit_number: The bit identifier (e.g., 'W00872')
        - kks: KKS identifier (must be unique)
        - comment: Optional comment about the bit
        - second_comment: Optional secondary comment
        - value: Optional value for the bit
        - forced_by: Who is forcing this bit (optional)
        - reason: Why this bit is being forced (optional)

        Returns:
        - The ID of the inserted or updated bit
        """
        conn = self.connect()

        try:
            # Truncate string values to respect database column limits
            if isinstance(resource_name, str) and len(resource_name) > 50:
                resource_name = resource_name[:50]
            if isinstance(bit_number, str) and len(bit_number) > 50:
                bit_number = bit_number[:50]
            if isinstance(kks, str) and len(kks) > 50:
                kks = kks[:50]
            if isinstance(comment, str) and len(comment) > 50:
                comment = comment[:50]
            if isinstance(second_comment, str) and len(second_comment) > 50:
                second_comment = second_comment[:50]
            if isinstance(value, str) and len(value) > 50:
                value = value[:50]

            with conn.cursor() as cursor:
                # First, get the resource_id from the resource name
                cursor.execute(
                    "SELECT resource_id FROM resource WHERE resource_name = %s",
                    (resource_name,)
                )
                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"Resource '{resource_name}' not found")

                resource_id = result[0]

                # Check if the bit already exists
                cursor.execute(
                    """
                    SELECT bit_id, force_Active
                    FROM resource_bit
                    WHERE resource_id = %s
                      AND bit_number = %s
                    """,
                    (resource_id, bit_number)
                )
                existing_bit = cursor.fetchone()

                if existing_bit:
                    bit_id = existing_bit[0]
                    was_active = existing_bit[1]

                    # Update existing bit and set force_Active to True
                    cursor.execute(
                        """
                        UPDATE resource_bit
                        SET kks            = %s,
                            comment        = %s,
                            second_comment = %s,
                            value          = %s,
                            force_Active   = TRUE
                        WHERE resource_id = %s
                          AND bit_number = %s RETURNING bit_id
                        """,
                        (kks, comment, second_comment, value, resource_id, bit_number)
                    )
                    bit_id = cursor.fetchone()[0]
                    print(f"Updated existing bit: {bit_number} in resource {resource_name}")

                    # If this bit wasn't active before but now is and we have a reason, record it
                    if not was_active and reason:
                        self._record_force_reason(cursor, bit_id, reason, forced_by)
                else:
                    # Insert new bit with force_Active set to True
                    print(f"Inserting new bit: {bit_number} in resource {resource_name}")
                    cursor.execute(
                        """
                        INSERT INTO resource_bit
                        (resource_id, bit_number, kks, comment, second_comment, value, force_Active)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE) RETURNING bit_id
                        """,
                        (resource_id, bit_number, kks, comment, second_comment, value)
                    )
                    bit_id = cursor.fetchone()[0]
                    print(f"Added new bit: {bit_number} to resource {resource_name}")

                    # Record the reason for forcing this bit if provided
                    if reason:
                        self._record_force_reason(cursor, bit_id, reason, forced_by)

                conn.commit()
                return bit_id

        except Exception as e:
            conn.rollback()
            print(f"Error in add_bit: {e}")
            print(f"SQL state: {e.pgcode if hasattr(e, 'pgcode') else 'unknown'}")
            raise e

    def _record_force_reason(self, cursor, bit_id, reason, forced_by=None):
        """
        Record why a bit was forced in the bit_force_reason table.

        Parameters:
        - cursor: Database cursor
        - bit_id: ID of the bit being forced
        - reason: Reason for forcing
        - forced_by: Who is forcing this bit
        """
        if forced_by:
            cursor.execute(
                """
                INSERT INTO bit_force_reason
                    (bit_id, reason, forced_by, forced_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (bit_id, reason, forced_by)
            )
        else:
            cursor.execute(
                """
                INSERT INTO bit_force_reason
                    (bit_id, reason, forced_at)
                VALUES (%s, %s, NOW())
                """,
                (bit_id, reason)
            )
        print(f"Recorded force reason for bit_id {bit_id}: {reason}")

    def deactivate_bit(self, resource_name, bit_number, deforced_by=None, reason=None):
        """
        Set force_Active = FALSE for a specific bit and record deforce timestamp.

        Parameters:
        - resource_name: Name of the resource
        - bit_number: Bit identifier
        - deforced_by: Who is deforcing this bit
        - reason: Reason for deforcing

        Returns:
        - True if successful, False otherwise
        """
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                # Get resource_id
                cursor.execute(
                    "SELECT resource_id FROM resource WHERE resource_name = %s",
                    (resource_name,)
                )
                result = cursor.fetchone()
                if not result:
                    print(f"Resource '{resource_name}' not found")
                    return False

                resource_id = result[0]

                # Get bit_id and current status
                cursor.execute(
                    """
                    SELECT bit_id, force_Active
                    FROM resource_bit
                    WHERE resource_id = %s
                      AND bit_number = %s
                    """,
                    (resource_id, bit_number)
                )
                result = cursor.fetchone()
                if not result:
                    print(f"Bit '{bit_number}' not found in resource '{resource_name}'")
                    return False

                bit_id, is_active = result

                # Only update deforced_at if the bit is currently active
                if is_active:
                    # Deactivate the bit
                    cursor.execute(
                        """
                        UPDATE resource_bit
                        SET force_Active = FALSE
                        WHERE bit_id = %s
                        """,
                        (bit_id,)
                    )

                    # Update the most recent force record with a deforced timestamp
                    cursor.execute(
                        """
                        UPDATE bit_force_reason
                        SET deforced_at = NOW()
                        WHERE force_id = (SELECT force_id
                                          FROM bit_force_reason
                                          WHERE bit_id = %s
                                            AND deforced_at IS NULL
                                          ORDER BY forced_at DESC
                            LIMIT 1
                            )
                        """,
                        (bit_id,)
                    )

                    # If we have new reason info for deforcing, add it
                    if reason:
                        if deforced_by:
                            reason_text = f"Deforced by {deforced_by}: {reason}"
                        else:
                            reason_text = f"Deforced: {reason}"

                        cursor.execute(
                            """
                            UPDATE bit_force_reason
                            SET reason = reason || ' | ' || %s
                            WHERE force_id = (SELECT force_id
                                              FROM bit_force_reason
                                              WHERE bit_id = %s
                                              ORDER BY forced_at DESC
                                LIMIT 1
                                )
                            """,
                            (reason_text, bit_id)
                        )

                    print(f"Deactivated bit: {bit_number} in resource {resource_name}")
                else:
                    print(f"Bit '{bit_number}' in resource '{resource_name}' is already inactive")

                conn.commit()
                return True

        except Exception as e:
            conn.rollback()
            print(f"Error deactivating bit: {e}")
            return False

    def get_bit(self, resource_name, bit_number):
        """
        Retrieve a bit from the database by resource name and bit number.

        Parameters:
        - resource_name: The name of the resource
        - bit_number: The bit identifier

        Returns:
        - A dictionary with the bit details or None if not found
        """
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT rb.bit_id,
                           rb.bit_number,
                           rb.kks,
                           rb.comment,
                           rb.second_comment,
                           rb.value,
                           r.resource_name,
                           rb.force_Active
                    FROM resource_bit rb
                             JOIN resource r ON rb.resource_id = r.resource_id
                    WHERE r.resource_name = %s
                      AND rb.bit_number = %s
                    """,
                    (resource_name, bit_number)
                )
                result = cursor.fetchone()

                if not result:
                    return None

                return {
                    'bit_id': result[0],
                    'bit_number': result[1],
                    'kks': result[2],
                    'comment': result[3],
                    'second_comment': result[4],
                    'value': result[5],
                    'resource_name': result[6],
                    'force_active': result[7]
                }

        except Exception as e:
            print(f"Error in get_bit: {e}")
            raise e

    def get_bit_history(self, resource_name, bit_number):
        """
        Retrieve force history for a bit.

        Parameters:
        - resource_name: The name of the resource
        - bit_number: The bit identifier

        Returns:
        - List of force history records
        """
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT bfr.force_id,
                           bfr.reason,
                           bfr.forced_by,
                           bfr.forced_at,
                           bfr.deforced_at
                    FROM bit_force_reason bfr
                             JOIN resource_bit rb ON bfr.bit_id = rb.bit_id
                             JOIN resource r ON rb.resource_id = r.resource_id
                    WHERE r.resource_name = %s
                      AND rb.bit_number = %s
                    ORDER BY bfr.forced_at DESC
                    """,
                    (resource_name, bit_number)
                )

                results = cursor.fetchall()
                history = []

                for row in results:
                    history.append({
                        'force_id': row[0],
                        'reason': row[1],
                        'forced_by': row[2],
                        'forced_at': row[3],
                        'deforced_at': row[4]
                    })

                return history

        except Exception as e:
            print(f"Error getting bit history: {e}")
            return []

    def reset_all_force_active(self, deforce_reason="Batch deforce operation"):
        """
        Reset all force_Active flags to False in the database.
        This can be used before a batch operation to start with a clean state.

        Parameters:
        - deforce_reason: Reason for deforcing all bits

        Returns:
        - Number of records updated
        """
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                # First, update all force reasons to include deforce timestamp
                cursor.execute(
                    """
                    UPDATE bit_force_reason
                    SET deforced_at = NOW(),
                        reason      = reason || ' | ' || %s
                    WHERE deforced_at IS NULL
                      AND bit_id IN (SELECT bit_id
                                     FROM resource_bit
                                     WHERE force_Active = TRUE)
                    """,
                    (deforce_reason,)
                )

                # Then, set all active bits to inactive
                cursor.execute(
                    """
                    UPDATE resource_bit
                    SET force_Active = FALSE
                    WHERE force_Active = TRUE
                    """
                )
                updated_count = cursor.rowcount
                conn.commit()
                return updated_count

        except Exception as e:
            conn.rollback()
            print(f"Error resetting force_Active flags: {e}")
            return 0

    def deactivate_bits_not_in_list(self, active_bit_list, resource_name=None, deforce_reason="Not included in import"):
        """
        Set force_Active = FALSE for all bits that are not in the provided list.

        Parameters:
        - active_bit_list: List of tuples (resource_name, bit_number) that should remain active
        - resource_name: Optional resource to limit the operation to
        - deforce_reason: Reason for deforcing bits

        Returns:
        - Number of records deactivated
        """
        if not active_bit_list:
            print("No active bits provided, skipping deactivation")
            return 0

        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                # Get the bit_ids that will be deforced
                if resource_name:
                    cursor.execute(
                        """
                        SELECT rb.bit_id
                        FROM resource_bit rb
                                 JOIN resource r ON rb.resource_id = r.resource_id
                        WHERE rb.force_Active = TRUE
                          AND r.resource_name = %s
                          AND NOT EXISTS (SELECT 1
                                          FROM (SELECT unnest(%s) AS res_name, unnest(%s) AS bit_num) AS active_bits
                                          WHERE active_bits.res_name = r.resource_name
                                            AND active_bits.bit_num = rb.bit_number)
                        """,
                        (resource_name,
                         [res for res, _ in active_bit_list],
                         [bit for _, bit in active_bit_list])
                    )
                else:
                    cursor.execute(
                        """
                        SELECT rb.bit_id
                        FROM resource_bit rb
                                 JOIN resource r ON rb.resource_id = r.resource_id
                        WHERE rb.force_Active = TRUE
                          AND NOT EXISTS (SELECT 1
                                          FROM (SELECT unnest(%s) AS res_name, unnest(%s) AS bit_num) AS active_bits
                                          WHERE active_bits.res_name = r.resource_name
                                            AND active_bits.bit_num = rb.bit_number)
                        """,
                        ([res for res, _ in active_bit_list],
                         [bit for _, bit in active_bit_list])
                    )

                bit_ids_to_deforce = [row[0] for row in cursor.fetchall()]

                # Update force_reason records for these bits
                if bit_ids_to_deforce:
                    cursor.execute(
                        """
                        UPDATE bit_force_reason
                        SET deforced_at = NOW(),
                            reason      = reason || ' | ' || %s
                        WHERE deforced_at IS NULL
                          AND bit_id = ANY (%s)
                        """,
                        (deforce_reason, bit_ids_to_deforce)
                    )

                # Create a temporary table to hold the active bits
                cursor.execute(
                    "CREATE TEMPORARY TABLE temp_active_bits (resource_name VARCHAR(100), bit_number VARCHAR(100))")

                # Insert the active bits into the temporary table
                for resource, bit in active_bit_list:
                    cursor.execute(
                        "INSERT INTO temp_active_bits (resource_name, bit_number) VALUES (%s, %s)",
                        (resource, bit)
                    )

                # Construct the SQL to update bits
                sql = """
                      UPDATE resource_bit rb
                      SET force_Active = FALSE FROM resource r
                      WHERE rb.resource_id = r.resource_id
                        AND rb.force_Active = TRUE
                        AND NOT EXISTS (
                          SELECT 1 FROM temp_active_bits tab
                          WHERE tab.resource_name = r.resource_name
                        AND tab.bit_number = rb.bit_number
                          )
                      """

                # Add resource filter if specified
                if resource_name:
                    sql += " AND r.resource_name = %s"
                    cursor.execute(sql, (resource_name,))
                else:
                    cursor.execute(sql)

                deactivated_count = cursor.rowcount

                # Clean up the temporary table
                cursor.execute("DROP TABLE temp_active_bits")

                conn.commit()
                print(f"Deactivated {deactivated_count} bits that were not in the import file")
                return deactivated_count

        except Exception as e:
            conn.rollback()
            print(f"Error deactivating bits: {e}")
            return 0

    def import_from_text_file(self, file_path, default_resource='NIET', forced_by=None, reason="Imported from file"):
        """
        Read data from a text file and import it into the database.

        Expected format: Each line contains a Python dictionary with fields like
        name_id, KKS, Comment, Second_comment, Value, etc.

        Parameters:
        - file_path: Path to the text file
        - default_resource: Default resource name to use if not specified in data
        - forced_by: Who is importing this data
        - reason: Reason for forcing bits

        Returns:
        - Number of records successfully imported
        """
        records_imported = 0
        updated_bits = []  # Track which bits are updated/added

        try:
            print(f"Opening file: {file_path}")
            with open(file_path, 'r') as file:
                lines = file.readlines()
                line_count = len(lines)

            print(f"File contains {line_count} lines")

            # Process each line in the file
            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip empty lines or comments
                if not line or line.startswith('#'):
                    continue

                # Special handling for the first line
                is_first_line = (line_num == 1)

                print(f"Processing line {line_num}/{line_count}: {line[:50]}...")
                try:
                    # Parse the line as a Python dictionary
                    # Use safe parsing with additional safety checks
                    try:
                        data = eval(line)  # Note: eval can be unsafe in production environments
                        if not isinstance(data, dict):
                            print(f"Line {line_num} does not evaluate to a dictionary: {type(data)}")
                            continue
                    except SyntaxError as se:
                        print(f"Line {line_num}: Syntax error in line: {se}")
                        continue
                    except Exception as e:
                        print(f"Line {line_num}: Error parsing line: {e}")
                        continue

                    # Extract values from the dictionary
                    bit_number = data.get('name_id')
                    kks = data.get('KKS')
                    comment = data.get('Comment')
                    second_comment = data.get('Second_comment')
                    value = data.get('Value')

                    # Debug output
                    print(f"  Extracted values - bit: {bit_number}, kks: {kks}, value: {value}")

                    # Get resource name - use 'resource' field if available or default
                    resource_name = data.get('resource')

                    # For the first line, if resource is not specified and KKS starts with "House",
                    # use "House" as the resource
                    if is_first_line and not resource_name and kks and kks.startswith('House.'):
                        resource_name = 'House'
                        print(f"  First line: KKS starts with 'House.', using 'House' as resource")
                    elif not resource_name:
                        resource_name = default_resource
                        print(f"  Missing resource name, using default: {default_resource}")

                    # Validate required fields
                    if not bit_number:
                        print(f"Line {line_num}: Missing bit number, skipping")
                        continue
                    if not kks:
                        print(f"Line {line_num}: Missing KKS, skipping")
                        continue

                    # Convert 'None' strings to None (Python null)
                    if isinstance(comment, str) and comment == 'None':
                        comment = None
                    if isinstance(second_comment, str) and second_comment == 'None':
                        second_comment = None
                    if isinstance(value, str) and value == 'None':
                        value = None

                    # Convert value to string if it's not already
                    if value is not None and not isinstance(value, str):
                        value = str(value)

                    # Create line-specific reason
                    line_reason = f"{reason} (line {line_num})"

                    # Add the bit to the database
                    try:
                        bit_id = self.add_bit(
                            resource_name=resource_name,
                            bit_number=bit_number,
                            kks=kks,
                            comment=comment,
                            second_comment=second_comment,
                            value=value,
                            forced_by=forced_by,
                            reason=line_reason
                        )

                        # Keep track of this bit being updated
                        updated_bits.append((resource_name, bit_number))

                        records_imported += 1
                        print(f"  Successfully imported bit: {resource_name}, {bit_number}, {kks}")
                    except Exception as e:
                        print(f"Error adding bit to database: {str(e)}")
                        raise

                except Exception as e:
                    print(f"Error importing line {line_num}: {str(e)}")
                    print(f"Line content: {line}")

            # Now set force_Active = FALSE for all bits that weren't in the import file
            if updated_bits:
                self.deactivate_bits_not_in_list(
                    updated_bits,
                    default_resource,
                    f"Not included in import from {file_path}"
                )
            else:
                print("No bits were imported, skipping deactivation step")

            return records_imported

        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return 0
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return 0

    def get_active_bits(self, resource_name=None):
        """
        Get all bits with force_Active set to True.

        Parameters:
        - resource_name: Optional filter by resource name

        Returns:
        - List of dictionaries with active bit details
        """
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                if resource_name:
                    # Get resource_id first
                    cursor.execute(
                        "SELECT resource_id FROM resource WHERE resource_name = %s",
                        (resource_name,)
                    )
                    result = cursor.fetchone()

                    if not result:
                        print(f"Resource '{resource_name}' not found")
                        return []

                    resource_id = result[0]

                    # Query bits filtered by resource and force_Active
                    cursor.execute(
                        """
                        SELECT rb.bit_id,
                               rb.bit_number,
                               rb.kks,
                               rb.comment,
                               rb.second_comment,
                               rb.value,
                               r.resource_name
                        FROM resource_bit rb
                                 JOIN resource r ON rb.resource_id = r.resource_id
                        WHERE rb.force_Active = TRUE
                          AND rb.resource_id = %s
                        ORDER BY rb.bit_number
                        """,
                        (resource_id,)
                    )
                else:
                    # Query all active bits across all resources
                    cursor.execute(
                        """
                        SELECT rb.bit_id,
                               rb.bit_number,
                               rb.kks,
                               rb.comment,
                               rb.second_comment,
                               rb.value,
                               r.resource_name
                        FROM resource_bit rb
                                 JOIN resource r ON rb.resource_id = r.resource_id
                        WHERE rb.force_Active = TRUE
                        ORDER BY r.resource_name, rb.bit_number
                        """
                    )

                results = cursor.fetchall()
                active_bits = []

                for result in results:
                    active_bits.append({
                        'bit_id': result[0],
                        'bit_number': result[1],
                        'kks': result[2],
                        'comment': result[3],
                        'second_comment': result[4],
                        'value': result[5],
                        'resource_name': result[6]
                    })

                return active_bits

        except Exception as e:
            print(f"Error retrieving active bits: {e}")
            return []

    def list_resources(self):
        """List all available resources in the database."""
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT resource_id, resource_name FROM resource")
                resources = cursor.fetchall()

                if not resources:
                    print("No resources found in the database.")
                    return []

                print("Available resources:")
                for resource_id, resource_name in resources:
                    print(f"  ID: {resource_id}, Name: {resource_name}")

                return resources

        except Exception as e:
            print(f"Error listing resources: {str(e)}")
            return []


# Example usage:
if __name__ == "__main__":
    # Replace with your actual database connection parameters
    db_params = {
        'host': 'localhost',
        'database': 'PLC_Forceringen',
        'user': 'postgres',
        'password': '123',
        'port': 5432
    }

    bit_manager = BitDatabaseManager(db_params)

    try:
        # List available resources to verify initialization
        print("\nChecking available resources in the database:")
        bit_manager.list_resources()

        # Reset all force_Active flags to start with a clean slate
        print("\nResetting all force_Active flags...")
        reset_count = bit_manager.reset_all_force_active("Starting fresh import run")
        print(f"Reset {reset_count} bits to force_Active = FALSE")

        # Import data from text.txt file - will set force_Active = TRUE for imported bits
        # and force_Active = FALSE for all others in that resource
        file_path = 'test.txt'
        print(f"\nImporting data from text file {file_path}...")
        text_imported_count = bit_manager.import_from_text_file(
            file_path,
            forced_by="System Import",
            reason="Scheduled import"
        )
        print(f"Successfully imported {text_imported_count} records from {file_path}")

        # Get and display active bits
        print("\nActive bits after import:")
        active_bits = bit_manager.get_active_bits()
        if active_bits:
            for bit in active_bits:
                print(f"{bit['resource_name']}: {bit['bit_number']} - {bit['kks']} = {bit['value']}")
        else:
            print("No active bits found after import!")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        bit_manager.close()