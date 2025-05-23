import psycopg2
from datetime import datetime
from class_bit_conversion import BitConversion
from class_making_querry import DataProcessor, FileReader
from class_database import DatabaseSearcher


class DatabaseConnector:
    """Base class for database connections with common functionality."""

    def __init__(self):
        self.conn = None
        self.cur = None

    def close(self):
        """Close database connection."""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def commit(self):
        """Commit transaction."""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """Rollback transaction."""
        if self.conn:
            self.conn.rollback()

    def execute(self, query, params=None):
        """Execute a query with parameters."""
        if self.cur:
            return self.cur.execute(query, params)
        raise Exception("No cursor available")

    def __enter__(self):
        """Support for context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        if exc_type:
            self.rollback()
        self.close()


class PostgreSQLManager(DatabaseConnector):
    """PostgreSQL specific database manager."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.conn = psycopg2.connect(**config)
        self.cur = self.conn.cursor()

    def insert_resource_bit(self, resource_name, bit_number, kks, comment, second_comment, value):
        """Insert a resource bit record."""
        self.execute(
            "SELECT insert_resource_bit(%s, %s, %s, %s, %s, %s);",
            (resource_name, bit_number, kks, comment, second_comment, value)
        )

    def reset_force_active_flags(self):
        """Reset all force_active flags in the database."""
        self.execute("UPDATE resource_bit SET force_active = FALSE;")


class DataImporter:
    """Handles data import from BitConversion to PostgreSQL."""

    def __init__(self, db_config, resource_default='NIET'):
        self.db_config = db_config
        self.RESOURCE_DEFAULT = resource_default

    def import_data(self, input_file_path, access_db_path):
        """Process and import data from source to database."""
        start = datetime.now()

        # Use with statement for database manager
        with PostgreSQLManager(self.db_config) as db:
            try:
                # Step 1: Reset flags
                db.reset_force_active_flags()
                db.commit()
                print("✅ Force active flags reset successfully.")

                # Step 2: Process and import data
                converted_data = self._get_converted_data(input_file_path, access_db_path)
                self._import_to_database(db, converted_data)

            except Exception as e:
                print(f"❌ Error: {e}")
                db.rollback()

        end = datetime.now()
        print(f"Time taken: {(end - start).total_seconds()} seconds")

    def _get_converted_data(self, input_file_path, access_db_path):
        """Get converted data from BitConversion."""
        # Read and process the input file
        words_list = FileReader(input_file_path).read_and_parse_file()
        processed_words = list(DataProcessor.convert_and_process_list(words_list))

        # Perform database search
        with DatabaseSearcher(access_db_path) as searcher:
            custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"
            results = searcher.search(processed_words, query_template=custom_query)

        # Convert bits
        bit_converter = BitConversion(results)
        return bit_converter.convert_variable_list()

    def _import_to_database(self, db, data_list):
        """Import converted data to database."""
        inserted_count = 0
        error_count = 0

        # Use batch commit for better performance
        batch_size = 100

        for i, data in enumerate(data_list):
            try:
                # Map the fields from BitConversion to the database fields
                bit_number = data.get('name_id')
                kks = str(data.get('KKS', 'None'))
                comment = str(data.get('Comment', 'None'))
                second_comment = str(data.get('Second_comment', 'None'))  # Using correct field name
                value = str(data.get('Value', 'NULL'))
                resource_name = data.get('resource') or self.RESOURCE_DEFAULT

                db.insert_resource_bit(resource_name, bit_number, kks, comment, second_comment, value)

                # Commit in batches for better performance
                if (i + 1) % batch_size == 0:
                    db.commit()
                    print(f"Progress: {i + 1} records processed")

                inserted_count += 1
            except Exception as bit_err:
                print(f"❌ Error inserting bit {data.get('name_id', '?')}: {bit_err}")
                db.rollback()
                error_count += 1

        # Final commit for any remaining records
        db.commit()
        print(f"✅ Data import completed: {inserted_count} records inserted, {error_count} errors")


# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'PLC_Forceringen',
    'user': 'postgres',
    'password': '123'
}
RESOURCE_DEFAULT = 'NIET'


def main():
    importer = DataImporter(DB_CONFIG, RESOURCE_DEFAULT)
    importer.import_data(
        input_file_path="BTEST_NIET.dat",
        access_db_path=r"D:/controller_l.mdb"
    )


if __name__ == "__main__":
    main()