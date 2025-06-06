"""
PLC Bit Repository Module

Information:
    This module provides asynchronous functionality for retrieving PLC bit data
    from a SQL Server database. It uses the unified DatabaseConnection class
    for database connectivity.

Date: 03/06/2025
Author: TOVY
"""

from Forceringen.util.unified_db_connection import DatabaseConnection

class PLCBitRepositoryAsync:
    """
    Information:
        A class for asynchronously retrieving PLC bit data from a SQL Server database.
        Uses the unified DatabaseConnection class for database connectivity.

    Parameters:
        Input: ConfigLoader instance containing database connection information

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, config_loader):
        """
        Information:
            Initialize the repository with a ConfigLoader instance.
            Creates a DatabaseConnection instance for database operations.

        Parameters:
            Input: config_loader - Instance of ConfigLoader containing DB info

        Date: 03/06/2025
        Author: TOVY
        """
        self.config_loader = config_loader
        self.db_connection = DatabaseConnection(config_loader)

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
            # Get a standalone async connection
            conn = await self.db_connection.get_connection(is_async=True)
            try:
                if resource_name:
                    sql = """
                        SELECT *
                        FROM plc_bits
                        WHERE PLC = :plc_name
                          AND resource = :resource_name
                    """
                    results = await conn.fetch_all(sql, {"plc_name": plc_name, "resource_name": resource_name})
                else:
                    sql = """
                        SELECT *
                        FROM plc_bits
                        WHERE PLC = :plc_name
                    """
                    results = await conn.fetch_all(sql, {"plc_name": plc_name})
                
                # Convert results to list of dictionaries
                return [dict(record) for record in results]
            finally:
                await conn.disconnect()
        except Exception as e:
            import traceback
            error_msg = f"Database error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return [("ERROR", error_msg)]