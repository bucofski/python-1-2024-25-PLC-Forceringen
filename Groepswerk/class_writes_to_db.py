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

    def add_bit(self, resource_name, bit_number, kks, comment=None, second_comment=None, value=None):
        """
        Add a new bit to the resource_bit table or update if it already exists.

        Parameters:
        - resource_name: The name of the resource
        - bit_number: The bit identifier (e.g., 'W00872')
        - kks: KKS identifier (must be unique)
        - comment: Optional comment about the bit
        - second_comment: Optional secondary comment
        - value: Optional value for the bit

        Returns:
        - The ID of the inserted or updated bit
        """
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                # First, get the resource_id from the resource name
                cursor.execute(
                    "SELECT resource_id FROM resource WHERE resource_name = %s",
                    (resource_name,)
                )
                result = cursor.fetchone()

                if not result:
                    raise ValueError(f"Resource '{resource_name}' not found in the database")

                resource_id = result[0]

                # Check if the bit already exists
                cursor.execute(
                    """
                    SELECT bit_id
                    FROM resource_bit
                    WHERE resource_id = %s
                      AND bit_number = %s
                    """,
                    (resource_id, bit_number)
                )
                existing_bit = cursor.fetchone()

                if existing_bit:
                    # Update existing bit
                    cursor.execute(
                        """
                        UPDATE resource_bit
                        SET kks            = %s,
                            comment        = %s,
                            second_comment = %s,
                            value          = %s
                        WHERE resource_id = %s
                          AND bit_number = %s RETURNING bit_id
                        """,
                        (kks, comment, second_comment, value, resource_id, bit_number)
                    )
                    bit_id = cursor.fetchone()[0]
                else:
                    # Insert new bit
                    cursor.execute(
                        """
                        INSERT INTO resource_bit
                            (resource_id, bit_number, kks, comment, second_comment, value)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING bit_id
                        """,
                        (resource_id, bit_number, kks, comment, second_comment, value)
                    )
                    bit_id = cursor.fetchone()[0]

                conn.commit()
                return bit_id

        except Exception as e:
            conn.rollback()
            raise e

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
                    SELECT rb.bit_id, rb.bit_number, rb.kks, rb.comment, rb.second_comment, rb.value, r.resource_name
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
                    'resource_name': result[6]
                }

        except Exception as e:
            raise e

    def add_force_reason(self, resource_name, bit_number, reason, forced_by=None):
        """
        Add a force reason for a bit.

        Parameters:
        - resource_name: The name of the resource
        - bit_number: The bit identifier
        - reason: The reason for forcing the bit
        - forced_by: Who forced the bit (optional)

        Returns:
        - The ID of the created force reason entry
        """
        conn = self.connect()

        try:
            with conn.cursor() as cursor:
                # Get the bit_id
                bit = self.get_bit(resource_name, bit_number)

                if not bit:
                    raise ValueError(f"Bit '{bit_number}' in resource '{resource_name}' not found")

                # Insert force reason
                cursor.execute(
                    """
                    INSERT INTO bit_force_reason (bit_id, reason, forced_by)
                    VALUES (%s, %s, %s) RETURNING force_id
                    """,
                    (bit['bit_id'], reason, forced_by)
                )
                force_id = cursor.fetchone()[0]

                conn.commit()
                return force_id

        except Exception as e:
            conn.rollback()
            raise e


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
        # Add a new bit
        bit_id = bit_manager.add_bit(
            resource_name='NIET',
            bit_number='W00873',
            kks='PilootTD.Interlock.NewBit',
            comment='New test bit',
            second_comment='[TD2,TDS,1202]',
            value='1'
        )
        print(f"Added/updated bit with ID: {bit_id}")

        # Add a force reason
        force_id = bit_manager.add_force_reason(
            resource_name='NIET',
            bit_number='W00873',
            reason='Testing purposes',
            forced_by='Test User'
        )
        print(f"Added force reason with ID: {force_id}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        bit_manager.close()
