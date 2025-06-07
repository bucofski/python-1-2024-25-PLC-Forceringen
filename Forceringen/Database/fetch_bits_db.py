"""
PLC Bit Repository Module

Information:
    This module provides asynchronous functionality for retrieving PLC bit data
    from a SQL Server database. It uses the unified DatabaseConnection class
    for database connectivity.

Date: 03/06/2025
Author: TOVY
"""

import asyncio
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
                print(f"results are :", results)
                return [record for record in results]

            finally:
                await conn.disconnect()
        except Exception as e:
            import traceback
            error_msg = f"Database error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return [("ERROR", error_msg)]

    async def fetch_bit_history(self, bit_data, selected_plc=None):
        """
        Information:
            Fetches the last 5 force history records for a selected bit from the database.
            Queries the last_5_force_reasons_per_bit view and returns the results.

        Parameters:
            Input: bit_data - Dictionary containing information about the selected bit
                  selected_plc - Optional PLC name override
            Output: List of history records from the database

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            # Use unified database connection
            conn = await self.db_connection.get_connection(is_async=True)

            try:
                plc_name = bit_data.get('PLC') or selected_plc
                resource_name = bit_data.get('resource')
                bit_number = bit_data.get('bit_number')

                # Query with SQL Server syntax (named parameters)
                history_query = """
                    SELECT *
                    FROM last_5_force_reasons_per_bit
                    WHERE PLC = :plc_name
                      AND resource = :resource_name
                      AND bit_number = :bit_number
                    ORDER BY forced_at DESC;
                """

                history_results = await conn.fetch_all(history_query, {
                    "plc_name": plc_name,
                    "resource_name": resource_name,
                    "bit_number": bit_number
                })

                print(f"Fetched {len(history_results)} history records for bit {bit_number}")
                return history_results

            finally:
                await conn.disconnect()

        except Exception as e:
            print(f"Error fetching bit history: {str(e)}")
            return []

if __name__ == "__main__":
    # You need to create an instance of the class and a config_loader
    # This is just an example - you'll need to import and create your actual config_loader
    from Forceringen.util.config_manager import ConfigLoader

    try:
        # Create config loader - adjust path as needed
        config_loader = ConfigLoader("../config/plc.yaml")

        # Create repository instance
        repository = PLCBitRepositoryAsync(config_loader)

        # Run the async method
        asyncio.run(repository.fetch_plc_bits("BTEST"))
    except Exception as e:
        print(f"Error running test: {e}")

    async def quick_test():
        try:
            config_loader = ConfigLoader("../config/plc.yaml")
            repository = PLCBitRepositoryAsync(config_loader)

            # Create test bit data dictionary
            bit_data = {
                'PLC': 'BTEST',
                'resource': 'NIET',
                'bit_number': 'G00000'  # Change this to an actual bit number in your database
            }

            history = await repository.fetch_bit_history(bit_data)
            print(f"Bit history: {history}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(quick_test())
