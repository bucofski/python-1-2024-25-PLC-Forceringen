"""
PLC Bit Repository Module

Information:
    This module provides asynchronous functionality for retrieving PLC bit data
    from a PostgreSQL database. It handles database connections and query execution
    using the asyncpg library.

Date: 03/06/2025
Author: TOVY
"""

import asyncpg

class PLCBitRepositoryAsync:
    """
    Information:
        A class for asynchronously retrieving PLC bit data from a PostgreSQL database.
        Manages database connections and provides methods to fetch data with filtering options.

    Parameters:
        Input: ConfigLoader instance containing database connection information

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, config_loader):
        """
        Information:
            Initialize the repository with a ConfigLoader instance.
            The config_loader must contain database connection parameters.

        Parameters:
            Input: config_loader - Instance of ConfigLoader containing DB info

        Date: 03/06/2025
        Author: TOVY
        """
        self.config_loader = config_loader

    async def _get_connection(self):
        db_config = self.config_loader.get_database_info()
        return await asyncpg.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
        )

    async def fetch_plc_bits(self, plc_name, resource_name=None):
        """
        Asynchronously fetch PLC bits from database, optionally filtered by resource.
        Args:
            plc_name: The name of the PLC to filter by
            resource_name: Optional resource name to filter by
        Returns:
            List of results from database
        """
        try:
            conn = await self._get_connection()
            try:
                if resource_name:
                    sql = """
                        SELECT *
                        FROM plc_bits
                        WHERE PLC = $1
                          AND resource = $2
                    """
                    results = await conn.fetch(sql, plc_name, resource_name)
                else:
                    sql = """
                        SELECT *
                        FROM plc_bits
                        WHERE PLC = $1
                    """
                    results = await conn.fetch(sql, plc_name)
                return [dict(record) for record in results]
            finally:
                await conn.close()
            return None
        except Exception as e:
            import traceback
            error_msg = f"Database error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return [("ERROR", error_msg)]