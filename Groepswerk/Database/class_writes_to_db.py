import json
from Groepswerk.PLC.class_bit_conversion import BitConversion
from Groepswerk.PLC.class_fetch_bits import PLCBitRepositoryAsync
from Groepswerk.util.class_config_loader import ConfigLoader
from Groepswerk.Database.class_making_querry import DataProcessor, FileReader
from Groepswerk.Database.class_database import DatabaseSearcher
import asyncio
import threading


class BitConversionDBWriter(BitConversion):
    """
    Inherits BitConversion. After conversion, writes entries to a database using batch procedure.
    Manages the 'force_active' column: sets force_active=True for given name_ids, and force_active=False for the rest.
    Uses PLCBitRepositoryAsync for database operations.
    """

    def __init__(self, data_list, config_loader):
        """
        Initialize with data list and ConfigLoader instance.

        Args:
            data_list: List of bit data to convert and write
            config_loader: Instance of ConfigLoader containing DB info
        """
        super().__init__(data_list)
        self.config_loader = config_loader
        self.repo = PLCBitRepositoryAsync(config_loader)

    async def write_to_database(self):
        """
        Asynchronously write the converted bit data to the database using a single batch procedure.
        Sets force_active=TRUE for the given entries and force_active=FALSE for others with the same PLC and resource.
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
        Run the database write operation in a separate thread.
        This avoids event loop conflicts when running in GUI contexts.
        """
        
        def run_async_in_thread():
            """Inner function to run in a separate thread"""
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