from datetime import datetime
import pyodbc
from class_making_querry import FileReader, DataProcessor


class DatabaseSearcher:
    def __init__(self, db_path):
        """Initialize the database connection string."""
        self.db_path = db_path
        self.connection_string = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={self.db_path};"
        )

    def connect(self):
        """Establish a connection to the database."""
        try:
            conn = pyodbc.connect(self.connection_string)
            return conn
        except pyodbc.Error as e:
            print(f"Database connection failed: {e}")
            return None

    def search(self, item_list, query_template):
        print(item_list)
        """
        Searches the database with a given query template.

        :param item_list: List of tuples [(search_name, associated_value), ...]
        :param query_template: SQL query template with {placeholders} for values.
        :return: List of dictionaries with search results.
        """
        if not item_list:
            print("Item list is empty. Query aborted.")
            return []

        search_items = [item[0] for item in item_list]
        associated_items = {item[0]: [item[1], item[2]] for item in item_list}

        conn = self.connect()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            placeholders = ", ".join("?" for _ in search_items)
            query = query_template.format(placeholders=placeholders)

            cursor.execute(query, search_items)
            results = cursor.fetchall()

            processed_results = []
            for row in results:
                name_mnemo = (row[1] or "").strip()
                mnemo_s = (
                    f"{(row[2] or '').strip()}.{(row[3] or '').strip()}.{(row[4] or '').strip()}"
                    if row[3] and (row[3] or "").strip()
                    else "None"
                )
                comment = (row[5] or "").strip() if (row[5] or "").strip() else "None"
                second_comment = (row[0] or "").strip() if (row[0] or "").strip() else "None"
                associated_item = associated_items.get(name_mnemo, "None")
                type_field = (row[6] or "").strip()

                processed_results.append({
                    'name_id': name_mnemo,
                    'KKS': mnemo_s,
                    'Comment': comment,
                    'Second_comment': second_comment,
                    'Type': type_field,
                    'Value': associated_item
                })

            return processed_results

        except pyodbc.Error as e:
            print(f"Database query error: {e}")
            return []

        finally:
            conn.close()


if __name__ == "__main__":
    start = datetime.now()

    # Initialize database searcher
    db_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"
    searcher = DatabaseSearcher(db_path)

    # Process input data
    file_reader = FileReader("for.dat")
    words_list = file_reader.read_and_parse_file()

    # Process the list using DataProcessor by creating an instance
    data_processor = DataProcessor(words_list)
    processed_list = data_processor.convert_and_process_list()

    # Custom query (optional)
    custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"

    # Perform search
    results = searcher.search(processed_list, query_template=custom_query)

    end = datetime.now()
    print(f"Time taken: {(end - start).total_seconds()} seconds")

    # Print results
    for row in results:
        print(row)
