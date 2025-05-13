from class_bit_conversion import BitConversion
import psycopg2


class BitConversionDBWriter(BitConversion):
    """
    Inherits BitConversion. After conversion, writes entries to a database table.
    Manages the 'active' column: sets active=True for given name_ids, and active=False for the rest (filtered by PLC and resource).
    """

    def __init__(self, data_list, db_conn, table_name):
        super().__init__(data_list)
        self.db_conn = db_conn
        self.table_name = table_name

    def write_to_database(self):
        processed_list = self.convert_variable_list()

        if not processed_list:
            return

        # Gather unique PLC and resource from the input list
        plc = processed_list[0].get("PLC")
        resource = processed_list[0].get("resource")
        name_ids = [row["name_id"] for row in processed_list]

        # Deactivate all for this PLC and resource
        deactivate_sql = f"""
            UPDATE {self.table_name}
            SET active = FALSE
            WHERE PLC = %s AND resource = %s
        """

        # Insert or update with active=True
        upsert_sql = f"""
            INSERT INTO {self.table_name}
            (name_id, PLC, resource, KKS, Comment, Second_comment, VAR_Type, Value, department_name, active)
            VALUES
            (%(name_id)s, %(PLC)s, %(resource)s, %(KKS)s, %(Comment)s, %(Second_comment)s, %(VAR_Type)s, %(Value)s, %(department_name)s, TRUE)
            ON CONFLICT (name_id) DO UPDATE SET
                PLC = EXCLUDED.PLC,
                resource = EXCLUDED.resource,
                KKS = EXCLUDED.KKS,
                Comment = EXCLUDED.Comment,
                Second_comment = EXCLUDED.Second_comment,
                VAR_Type = EXCLUDED.VAR_Type,
                Value = EXCLUDED.Value,
                department_name = EXCLUDED.department_name,
                active = TRUE
        """

        with self.db_conn:
            with self.db_conn.cursor() as cur:
                # Set all to inactive first
                cur.execute(deactivate_sql, (plc, resource))
                # Upsert current records as active
                for row in processed_list:
                    cur.execute(upsert_sql, row)
