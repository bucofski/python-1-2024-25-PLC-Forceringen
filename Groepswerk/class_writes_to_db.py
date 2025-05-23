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
        # Get resource name from file name
        import os
        file_name = os.path.basename(input_file_path)
        # Assuming filename format is like "BTEST_NIET.dat"
        parts = file_name.replace('.dat', '').split('_', 1)
        resource = parts[1] if len(parts) > 1 else "NIET"  # Default to NIET if not found
        
        # Read and process the input file
        words_list = FileReader(input_file_path).read_and_parse_file()
        processed_words = list(DataProcessor.convert_and_process_list(words_list))

        # Perform database search
        with DatabaseSearcher(access_db_path) as searcher:
            custom_query = f"SELECT *, SecondComment FROM {resource} WHERE Name IN ({{placeholders}})"
            results = searcher.search(processed_words, query_template=custom_query, resource=resource)

        # Convert bits
        bit_converter = BitConversion(results)
        return bit_converter.convert_variable_list()

    def _import_to_database(self, db, data_list):
        """Import converted data to database."""
        inserted_count = 0
        error_count = 0
        resources_stats = {}  # Track statistics by resource
        errors = []  # Track all errors in one list

        # Reset force active flags
        try:
            db.reset_force_active_flags()
            db.commit()
            print("✅ Force active flags reset successfully.")
        except Exception as e:
            print(f"❌ Error resetting force active flags: {e}")
            db.rollback()

        # Process each record separately with its own transaction
        for i, data in enumerate(data_list):
            # Start a fresh transaction for each record
            try:
                # Extract and validate fields
                bit_number = data.get('name_id')
                if not bit_number:
                    raise ValueError("Missing required 'name_id' field")

                kks = data.get('KKS')
                # Ensure kks is a string if it exists
                kks = str(kks) if kks is not None else None

                # Check for invalid KKS values
                if kks is None or kks.strip() == '' or kks.lower() == 'none':
                    errors.append({
                        'name_id': bit_number,
                        'error': "Missing or invalid KKS value"
                    })
                    error_count += 1
                    continue  # Skip this record

                # Get other fields
                comment = str(data.get('Comment', ''))
                second_comment = str(data.get('Second_comment', ''))
                value = str(data.get('Value', ''))

                # Get resource
                resource_name = data.get('resource')
                if not resource_name:
                    raise ValueError("Missing required 'resource' field")

                # Track resource statistics
                if resource_name not in resources_stats:
                    resources_stats[resource_name] = 0

                # Insert the record - each in its own transaction
                db.insert_resource_bit(
                    resource_name,
                    bit_number,
                    kks,
                    comment,
                    second_comment,
                    value
                )

                # Commit immediately for this record
                db.commit()

                # Update statistics
                resources_stats[resource_name] += 1
                inserted_count += 1

                # Show progress
                if (i + 1) % 100 == 0 or i + 1 == len(data_list):
                    print(f"Progress: {i + 1}/{len(data_list)} records processed")

            except ValueError as val_err:
                # Skip and record validation errors
                errors.append({
                    'name_id': data.get('name_id', '?'),
                    'error': str(val_err)
                })
                error_count += 1

            except Exception as e:
                # Record other errors
                error_message = str(e)
                errors.append({
                    'name_id': data.get('name_id', '?'),
                    'error': error_message
                })
                error_count += 1
                # Rollback this record's transaction
                db.rollback()

        # Print summary statistics
        print(f"\n===== Import Summary =====")
        print(f"Total records processed: {len(data_list)}")
        print(f"Successfully inserted: {inserted_count}")
        print(f"Total errors: {error_count}")

        # Print resource distribution
        print("\nResource distribution:")
        for resource, count in sorted(resources_stats.items()):
            print(f"  - {resource}: {count} records")

        # Print all errors
        if errors:
            print("\nErrors encountered:")
            for i, record in enumerate(errors[:20], 1):  # Show first 20 errors
                print(f"  {i}. Bit {record['name_id']}: {record['error']}")
            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more")

        return inserted_count, error_count

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