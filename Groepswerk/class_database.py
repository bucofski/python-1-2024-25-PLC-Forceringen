from datetime import datetime
import pyodbc
from class_making_querry import FileReader, DataProcessor

class DatabaseSearcher:
    def __init__(self, db_path):
        """Initialize the database connection string and connection to None."""
        self.db_path = db_path
        self.connection_string = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={self.db_path};"
        )
        self.conn = None

    def __enter__(self):
        """Context management entry: connect to the database."""
        self.conn = pyodbc.connect(self.connection_string)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context management exit: close the connection."""
        if self.conn:
            self.conn.close()

    def search(self, item_list, query_template):
        """
        Searches the database with a given query template.

        :param item_list: List of tuples [(search_name, value, extra_value), ...]
        :param query_template: SQL query template with {placeholders} for values.
        :return: List of dictionaries with search results.
        """
        if not item_list:
            print("Item list is empty. Query aborted.")
            return []

        # Prepare search terms and mapping outside query loop
        search_items = [item[0] for item in item_list]
        associated_items = {item[0]: [item[1], item[2]] for item in item_list}

        # Batched execution if item_list is very large (optional - Access might not like >1000 in IN)
        batch_size = 800  # safe upper limit for Access SQL
        processed_results = []
        cursor = self.conn.cursor()

        for i in range(0, len(search_items), batch_size):
            batch = search_items[i:i+batch_size]
            placeholders = ", ".join("?" for _ in batch)
            query = query_template.format(placeholders=placeholders)
            try:
                cursor.execute(query, batch)
                results = cursor.fetchall()
                for row in results:
                    name_mnemo = (row[1] or "").strip()
                    mnemo_s = (
                        f"{(row[2] or '').strip()}.{(row[3] or '').strip()}.{(row[4] or '').strip()}"
                        if row[3] and (row[3] or "").strip()
                        else "None"
                    )
                    comment = (row[5] or "").strip() or "None"
                    second_comment = (row[0] or "").strip() or "None"
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
            except pyodbc.Error as e:
                print(f"Database query error: {e}")
                continue  # Try remaining batches

        return processed_results

if __name__ == "__main__":
    start = datetime.now()
    db_path = r"C:/Users/SIDTOVY/OneDrive - ArcelorMittal/Desktop/controller_l.mdb"

    # process and search within a single context (connection)
    with DatabaseSearcher(db_path) as searcher:
        file_reader = FileReader("for.dat")
        words_list = file_reader.read_and_parse_file()
        processed_list = list(DataProcessor.convert_and_process_list(words_list))
        custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"
        #custom_query = "SELECT Name, MnemoK, [MnemoK'], MnemoS, Comment, SecondComment, Type FROM NIET WHERE Name IN ({placeholders})"
        results = searcher.search(processed_list, query_template=custom_query)

    end = datetime.now()
    print(f"Time taken: {(end - start).total_seconds()} seconds")
    for row in results:
        print(row)