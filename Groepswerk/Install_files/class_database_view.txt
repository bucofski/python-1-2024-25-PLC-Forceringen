import psycopg2
import pandas as pd
from psycopg2 import sql


class DatabaseViewConnector:
    def __init__(self, db_config):
        """
        Initialize the database connector with connection parameters

        Parameters:
        -----------
        db_config : dict
            Dictionary containing database connection parameters
        """
        self.db_config = db_config
        self.connection = None
        self.cursor = None

    def connect(self):
        """Establish connection to the database"""
        try:
            self.connection = psycopg2.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 5432),
                database=self.db_config.get('database'),
                user=self.db_config.get('user'),
                password=self.db_config.get('password')
            )
            self.cursor = self.connection.cursor()
            print(f"Connected to database: {self.db_config.get('database')}")
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("Database connection closed")

    def __enter__(self):
        """Support for context manager"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support for context manager"""
        self.disconnect()

    def execute_view_query(self, query):
        """
        Execute a query and return results as DataFrame

        Parameters:
        -----------
        query : str
            SQL query to execute

        Returns:
        --------
        pandas.DataFrame
            Query results as DataFrame
        """
        if not self.connection:
            if not self.connect():
                return pd.DataFrame()

        try:
            self.cursor.execute(query)
            columns = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            print(f"Query execution error: {e}")
            return pd.DataFrame()

    def get_view(self, view_name):
        """
        Get data from a named view

        Parameters:
        -----------
        view_name : str
            Name of the view to query

        Returns:
        --------
        pandas.DataFrame
            View data as DataFrame
        """
        query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(view_name))
        return self.execute_view_query(query.as_string(self.connection))
