import json
from class_bit_conversion import BitConversion
from class_fetch_bits import PLCBitRepositoryAsync
from class_config_loader import ConfigLoader
from class_making_querry import DataProcessor, FileReader
from class_database import DatabaseSearcher
import asyncio


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

        if not plc_name or not resource_name:
            print("Error: Missing PLC or resource name in data")
            return

        # Convert processed list to JSON format for the procedure
        bits_json = json.dumps(processed_list)

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


if __name__ == "__main__":
    async def main():
        try:
            config_loader = ConfigLoader("plc.yaml")
            words_list = FileReader("BTEST_NIET.dat").read_and_parse_file()
            data_list = list(DataProcessor.convert_and_process_list(words_list))

            db_path = r"D:/controller_l.mdb"
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