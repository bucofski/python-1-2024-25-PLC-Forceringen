import psycopg2
from datetime import datetime
from class_bit_conversion import BitConversion
from class_making_querry import DataProcessor, FileReader
from class_database import DatabaseSearcher


class DatabaseManager:
    def __init__(self, config):
        self.conn = psycopg2.connect(**config)
        self.cur = self.conn.cursor()

    def close(self):
        self.cur.close()
        self.conn.close()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def insert_resource_bit(self, resource_name, bit_number, kks, comment, second_comment, value):
        self.cur.execute(
            "SELECT insert_resource_bit(%s, %s, %s, %s, %s, %s);",
            (resource_name, bit_number, kks, comment, second_comment, value)
        )

    def reset_force_active_flags(self):
        """Reset all force_active flags in the database."""
        self.cur.execute("UPDATE resource_bit SET force_active = FALSE;")


DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'PLC_Forceringen',
    'user': 'postgres',
    'password': '123'
}
RESOURCE_DEFAULT = 'NIET'


def main():
    start = datetime.now()

    # Initialize database manager
    db = DatabaseManager(DB_CONFIG)

    # Step 1: Reset all force_active flags
    try:
        db.reset_force_active_flags()
        db.commit()
        print("✅ Force active flags reset successfully.")
    except Exception as reset_err:
        print(f"❌ Error resetting force_active flags: {reset_err}")
        db.rollback()

    # Step 2: Get data from BitConversion instead of reading from test.txt
    try:
        # Read and process the input file
        words_list = FileReader("BTEST_NIET.dat").read_and_parse_file()
        processed_words = list(DataProcessor.convert_and_process_list(words_list))

        # Perform database search
        db_path = r"D:/controller_l.mdb"
        custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"
        with DatabaseSearcher(db_path) as searcher:
            results = searcher.search(processed_words, query_template=custom_query)

        # Convert bits
        bit_converter = BitConversion(results)
        converted_data = bit_converter.convert_variable_list()

        # Insert the converted data into PostgreSQL database
        inserted_count = 0
        error_count = 0

        for data in converted_data:
            try:
                # Map the fields from BitConversion to the database fields
                bit_number = data.get('name_id')
                kks = str(data.get('KKS', 'None'))
                comment = str(data.get('Comment', 'None'))
                second_comment = str(data.get('SecondComment', 'None'))
                value = str(data.get('Value', 'NULL'))
                resource_name = data.get('resource', RESOURCE_DEFAULT)

                db.insert_resource_bit(resource_name, bit_number, kks, comment, second_comment, value)
                db.commit()
                inserted_count += 1
            except Exception as bit_err:
                print(f"❌ Error inserting bit {data.get('name_id', '?')}: {bit_err}")
                db.rollback()
                error_count += 1

        print(f"✅ Data import completed: {inserted_count} records inserted, {error_count} errors")
    except Exception as e:
        print(f"❌ Error processing bit data: {e}")

    end = datetime.now()
    print(f"Time taken: {(end - start).total_seconds()} seconds")

    db.close()


if __name__ == "__main__":
    main()
