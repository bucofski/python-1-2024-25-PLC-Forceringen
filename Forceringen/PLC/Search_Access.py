"""
Database Search Module

Information:
    This module provides functionality for connecting to Microsoft Access databases and
    performing searches with batch processing. It's designed to handle large datasets
    efficiently and integrate with other components of the system.

Date: 03/06/2025
Author: TOVY
"""

from datetime import datetime
import pyodbc
from Forceringen.PLC.convert_dat_file import FileReader, DataProcessor
from Forceringen.util.config_manager import ConfigLoader


class DatabaseSearcher:
    """
    Information:
        A class for searching Microsoft Access databases using context management.
        Handles database connections, query execution, and result processing.

    Parameters:
        Input: Path to an Access database file (*.mdb, *.accdb)

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, dbs_path):
        """
        Information:
            Initialize the database searcher with a path to the database file.
            Sets up the connection string but doesn't establish a connection yet.

        Parameters:
            Input: dbs_path - Path to the Access database file

        Date: 03/06/2025
        Author: TOVY
        """
        self.db_path = dbs_path
        self.connection_string = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={self.db_path};"
        )
        self.conn = None

    def __enter__(self):
        """
        Information:
            Context management entry method that establishes a database connection.
            Used when the class is instantiated in a 'with' statement.

        Parameters:
            Output: Self reference for use in the context manager

        Date: 03/06/2025
        Author: TOVY
        """
        self.conn = pyodbc.connect(self.connection_string)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Information:
            Context management exit method that closes the database connection.
            Automatically called when exiting a 'with' block.

        Parameters:
            Input: exc_type - Exception type if raised
                  exc_val - Exception value if raised
                  exc_tb - Exception traceback if raised

        Date: 03/06/2025
        Author: TOVY
        """
        if self.conn:
            self.conn.close()

    def search(self, item_list, query_template, department_name, plc, resource):
        """
        Information:
            Searches the database with a given query template.
            Processes search results into a standardized dictionary format.
            Uses batch processing to handle large item lists efficiently.

        Parameters:
            Input: item_list - List of tuples [(search_name, value, extra_value), ...]
                  query_template - SQL query template with {placeholders} for values
                  department_name - String from YAML configuration
                  plc - PLC name (e.g. 'BTEST')
                  resource - Resource name (e.g. 'NIET')
            Output: List of dictionaries with search results

        Date: 03/06/2025
        Author: TOVY
        """

        processed_results = []

        if not item_list:
            print("Item list is empty. Query aborted.")
            processed_results.append({
                        "department_name": department_name,
                        "PLC": plc,
                        "resource": resource
                    })
            return processed_results


        # Prepare search terms and mapping outside query loop
        search_items = [item[0] for item in item_list]
        associated_items = {item[0]: [item[1], item[2]] for item in item_list}

        # Batched execution if item_list is very large (optional, Access might not like >1000 in IN)
        batch_size = 800  # safe upper limit for Access SQL
        processed_results = []
        cursor = self.conn.cursor()

        for i in range(0, len(search_items), batch_size):
            batch = search_items[i:i + batch_size]
            placeholders = ", ".join("?" for _ in batch)
            query = query_template.format(placeholders=placeholders)
            try:
                cursor.execute(query, batch)
                results_ = cursor.fetchall()
                for row in results_:
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
                        'VAR_Type': type_field,
                        'Value': associated_item,
                        "department_name": department_name,
                        "PLC": plc,
                        "resource": resource
                    })
            except pyodbc.Error as e:
                print(f"Database query error: {e}")
                continue  # Try remaining batches
        return processed_results


if __name__ == "__main__":
    """
        Information:
            Main execution block that demonstrates the usage of the DatabaseSearcher class.
            This script:
            1. Loads configuration from a YAML file
            2. Establishes a database connection
            3. Reads and processes data from a file
            4. Executes a database query with the processed data
            5. Prints the time taken and the search results
    """
    start = datetime.now()

    # Use ConfigLoader to load configuration from YAML
    config_loader = ConfigLoader("../config/plc.yaml")
    config = config_loader.config
    department_name = config.get("department_name", "UNKNOWN")

    db_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"
    # db_path = r"C:/Users/SIDTOVY/OneDrive - ArcelorMittal/Desktop/controller_l.mdb"

    # process and search within a single context (connection)
    with DatabaseSearcher(db_path) as searcher:
        file_reader = FileReader("../tests/BTEST_NIET.dat")
        words_list = file_reader.read_and_parse_file()
        processed_list = list(DataProcessor.convert_and_process_list(words_list))
        custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"
        results = searcher.search(processed_list, query_template=custom_query, department_name="BT2", plc="BTEST", resource="NIET")

    end = datetime.now()
    print(f"Time taken: {(end - start).total_seconds()} seconds")
    for row_ in results:
        print(row_)
