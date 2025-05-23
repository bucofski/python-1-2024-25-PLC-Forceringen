import psycopg2

class PLCBitRepository:
    def __init__(self, config_loader):
        """
        Initialize with a ConfigLoader instance.
        Args:
            config_loader: Instance of ConfigLoader containing DB info.
        """
        self.config_loader = config_loader

    def _get_connection(self):
        db_config = self.config_loader.get_database_info()
        return psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password'],
        )

    def fetch_plc_bits(self, plc_name, resource_name=None):
        """
        Fetch PLC bits from database, optionally filtered by resource.
        Args:
            plc_name: The name of the PLC to filter by
            resource_name: Optional resource name to filter by
        Returns:
            List of results from database
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            if resource_name:
                sql = """
                        SELECT *
                        FROM plc_bits
                        WHERE PLC = %s
                        AND resource = %s
                    """
                cur.execute(sql, (plc_name, resource_name))
            else:
                sql = """
                        SELECT *
                        FROM plc_bits
                        WHERE PLC = %s
                    """
                cur.execute(sql, (plc_name,))

            results = cur.fetchall()
            cur.close()
            conn.close()
            return results
        except Exception as e:
            import traceback
            error_msg = f"Database error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)  # Optionally, log this instead.
            return [("ERROR", error_msg)]  # Yield error to UI