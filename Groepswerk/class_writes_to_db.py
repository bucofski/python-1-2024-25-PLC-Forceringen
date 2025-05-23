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
        """
        Call the PostgreSQL stored function to insert a resource bit.
        The function handles PLC lookup and resource validation.
        """
        self.execute(
            "SELECT insert_resource_bit(%s, %s, %s, %s, %s, %s);",
            (resource_name, bit_number, kks, comment, second_comment, value)
        )

    def reset_force_active_flags(self):
        """Reset all force_active flags in the database."""
        self.execute("UPDATE resource_bit SET force_active = FALSE;")


class DataImporter:
    """Handles data import from BitConversion to PostgreSQL."""

    def __init__(self, db_config):
        self.db_config = db_config

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
        resources_stats = {}  # Track statistics by resource
        skipped_records = []  # Track records skipped due to missing required fields

        # Use batch commit for better performance
        batch_size = 100

        for i, data in enumerate(data_list):
            try:
                # Map the fields from BitConversion to the database fields
                bit_number = data.get('name_id')
                if not bit_number:
                    raise ValueError("Missing required 'name_id' field")

                kks = str(data.get('KKS', ''))
                if not kks:
                    raise ValueError("Missing required 'KKS' field")

                comment = str(data.get('Comment', ''))
                second_comment = str(data.get('Second_comment', ''))
                value = str(data.get('Value', ''))

                # Get resource - could be 'NIET' or another value like 'House'
                resource_name = data.get('resource')
                if not resource_name:
                    raise ValueError("Missing required 'resource' field")

                # Track resource statistics
                if resource_name not in resources_stats:
                    resources_stats[resource_name] = 0
                resources_stats[resource_name] += 1

                # Call the PostgreSQL function to insert the bit
                # Note: The PostgreSQL function handles PLC lookup (hardcoded to 'BTEST')
                db.insert_resource_bit(
                    resource_name,
                    bit_number,
                    kks,
                    comment,
                    second_comment,
                    value
                )

                # Commit in batches for better performance
                if (i + 1) % batch_size == 0:
                    db.commit()
                    print(f"Progress: {i + 1} records processed")

                inserted_count += 1
            except ValueError as val_err:
                # These are validation errors for missing fields
                skipped_record = {
                    'name_id': data.get('name_id', '?'),
                    'error': str(val_err)
                }
                skipped_records.append(skipped_record)
                error_count += 1
            except Exception as bit_err:
                # These are database errors (e.g., resource not found)
                print(f"❌ Error inserting bit {data.get('name_id', '?')}: {bit_err}")
                error_count += 1

        # Final commit for any remaining records
        db.commit()

        # Print summary statistics
        print(f"✅ Data import completed: {inserted_count} records inserted, {error_count} errors")

        if skipped_records:
            print("\nSkipped records due to missing required fields:")
            for i, record in enumerate(skipped_records[:10], 1):  # Show first 10 only
                print(f"  {i}. Bit {record['name_id']}: {record['error']}")

            if len(skipped_records) > 10:
                print(f"  ... and {len(skipped_records) - 10} more")

        print("\nResource distribution:")
        for resource, count in sorted(resources_stats.items()):
            print(f"  - {resource}: {count} records")


# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'PLC_Forceringen',
    'user': 'postgres',
    'password': '123'
}


def main():
    importer = DataImporter(DB_CONFIG)
    importer.import_data(
        input_file_path="BTEST_NIET.dat",
        access_db_path=r"D:/controller_l.mdb"
    )


if __name__ == "__main__":
    main()