"""
Database Writer Module

Information:
    This module provides functionality for converting bit data and writing it to a database.
    It handles batch operations, async database connections, and threading for GUI compatibility.

Date: 03/06/2025
Author: [Insert your name here]
"""

import json
from Groepswerk.PLC.Value_convertion import BitConversion
from Groepswerk.Database.fetch_bits_db import PLCBitRepositoryAsync
from Groepswerk.util.config_manager import ConfigLoader
from Groepswerk.PLC.convert_dat_file import DataProcessor, FileReader
from Groepswerk.PLC.Search_Access import DatabaseSearcher
import asyncio
import threading


class BitConversionDBWriter(BitConversion):
    """
    Information:
        Inherits from BitConversion class to extend its functionality.
        After converting bit data, this class writes entries to a database using batch procedures.
        Manages the 'force_active' column: sets force_active=True for given name_ids,
        and force_active=False for the rest with the same PLC and resource.

    Parameters:
        Input: List of bit data to convert and write, ConfigLoader instance

    Date: 03/06/2025
    Author: CHIV
    """

    def __init__(self, data_list, config_loader):
        """
        Information:
            Initialize with data list and ConfigLoader instance.
            Sets up the database repository connection.

        Parameters:
            Input: data_list - List of bit data to convert and write
                  config_loader - Instance of ConfigLoader containing DB info

        Date: 03/06/2025
        Author: CHIV
        """
        super().__init__(data_list)
        self.config_loader = config_loader
        self.repo = PLCBitRepositoryAsync(config_loader)

    async def write_to_database(self):
        """
        Information:
            Asynchronously write the converted bit data to the database using a single batch procedure.
            Sets force_active=TRUE for the given entries and force_active=FALSE for others
            with the same PLC and resource.
            Uses a stored procedure to handle the database operations efficiently.

        Date: 03/06/2025
        Author: CHIV
        """
        processed_list = self.convert_variable_list()
        if not processed_list:
            print("No data to process")
            return
        # Get PLC and resource from first record (assuming all records have same PLC/resource)
        plc_name = processed_list[0].get("PLC")
        resource_name = processed_list[0].get("resource")
        bit_name = processed_list[0].get("name_id")

        print(f"PLC: {plc_name}, Resource: {resource_name}")
        if not plc_name or not resource_name:
            print("Error: Missing PLC or resource name in data")
            return
        elif plc_name and resource_name and not bit_name:
            processed_list = []
            bits_json = json.dumps(processed_list)
        else:
            bits_json = json.dumps(processed_list)

        # Convert processed list to JSON format for the procedure

        conn = await self.repo._get_connection()
        try:
            print(f"Processing {len(processed_list)} bits for PLC: {plc_name}, Resource: {resource_name}")

            # Call the batch procedure
            result = await conn.fetchrow(
                "SELECT * FROM upsert_plc_bits($1, $2, $3::jsonb)",
                plc_name, resource_name, bits_json
            )

            # Check result
            if result['success']:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")

        except Exception as e:
            print(f"Database error: {e}")
        finally:
            await conn.close()

    def write_to_database_threaded(self):
        """
        Information:
            Run the database write operation in a separate thread.
            This avoids event loop conflicts when running in GUI contexts.
            Creates a new event loop for the thread and manages its lifecycle.

        Date: 03/06/2025
        Author: CHIV
        """
        
        def run_async_in_thread():
            """
            Information:
                Inner function to run in a separate thread.
                Creates and manages an event loop for asynchronous operations.

            Date: 03/06/2025
            Author: CHIV
            """
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the async database operation to completion
                return loop.run_until_complete(self.write_to_database())
            finally:
                loop.close()
        
        # Create and start a thread for the database operation
        thread = threading.Thread(target=run_async_in_thread)
        thread.start()
        
        # Wait for the thread to complete (blocks the calling thread)
        thread.join()
        print("Database write completed (via threading)")


if __name__ == "__main__":
    async def main():
        """
        Information:
            Asynchronous main function that orchestrates the full data processing pipeline.
            Handles configuration loading, file reading, data processing, database queries,
            and finally writing the results back to the database.

        Date: 03/06/2025
        Author: CHIV
        """
        try:
            config_loader = ConfigLoader("../config/plc.yaml")
            words_list = FileReader("../tests/BTEST_NIET.dat").read_and_parse_file()
            data_list = list(DataProcessor.convert_and_process_list(words_list))

            db_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"
            custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"

            with DatabaseSearcher(db_path) as searcher:
                results = searcher.search(data_list, query_template=custom_query, department_name="bt2", plc="BTEST",
                                          resource="NIET")

            # Run the database write in async context
            writer = BitConversionDBWriter(results, config_loader)
            await writer.write_to_database()

        except Exception as e:
            print(f"Application error: {e}")


    asyncio.run(main())