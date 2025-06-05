import inspect
import psycopg2
import asyncpg


class DatabaseConnection:
    """
    Information:
        Unified database connection class that provides both synchronous and asynchronous
        database connections with a consistent interface. Supports context managers,
        automatic async detection, and connection management.

    Parameters:
        Input: Configuration loader object that provides database connection parameters

    Date: 03/06/2025
    Author: TOVY
    """

    def __init__(self, config_loader):
        """
        Information:
            Initialize with a configuration loader that provides database connection parameters.
            Sets up instance variables for storing connection objects.

        Parameters:
            Input: config_loader - An instance that provides get_database_info() method

        Date: 03/06/2025
        Author: TOVY
        """
        self.config_loader = config_loader
        # For storing connections when using instance mode
        self.sync_connection = None
        self.sync_cursor = None
        self.async_connection = None

    def _get_db_config(self):
        """
        Information:
            Get database configuration from the config loader with default values.
            This is an internal helper method used by connection methods.

        Parameters:
            Output: Dictionary with database connection parameters

        Date: 03/06/2025
        Author: TOVY
        """
        db_config = self.config_loader.get_database_info()
        return {
            "host": db_config.get("host", "localhost"),
            "port": db_config.get("port", 5432),
            "database": db_config.get("database"),
            "user": db_config.get("user"),
            "password": db_config.get("password")
        }

    def connect(self):
        """
        Information:
            Establish a synchronous connection to the database.
            Stores the connection and cursor as instance attributes.
            Provides feedback about connection status.

        Parameters:
            Output: Boolean indicating connection success or failure

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            db_config = self._get_db_config()
            self.sync_connection = psycopg2.connect(**db_config)
            self.sync_cursor = self.sync_connection.cursor()
            print(f"Connected to database: {db_config['database']}")
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    async def connect_async(self):
        """
        Information:
            Establish an asynchronous connection to the database.
            Stores the connection as an instance attribute.
            Provides feedback about connection status.

        Parameters:
            Output: Boolean indicating connection success or failure

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            db_config = self._get_db_config()
            self.async_connection = await asyncpg.connect(**db_config)
            print(f"Connected asynchronously to database: {db_config['database']}")
            return True
        except Exception as e:
            print(f"Asynchronous database connection error: {e}")
            return False

    def disconnect(self):
        """
        Information:
            Close the synchronous database connection and cursor.
            Resets instance attributes to None after closing.
            Provides feedback when connection is closed.

        Date: 03/06/2025
        Author: TOVY
        """
        if self.sync_cursor:
            self.sync_cursor.close()
            self.sync_cursor = None
        if self.sync_connection:
            self.sync_connection.close()
            self.sync_connection = None
            print("Database connection closed")

    async def disconnect_async(self):
        """
        Information:
            Close the asynchronous database connection.
            Resets instance attribute to None after closing.
            Provides feedback when connection is closed.

        Date: 03/06/2025
        Author: TOVY
        """
        if self.async_connection:
            await self.async_connection.close()
            self.async_connection = None
            print("Asynchronous database connection closed")

    async def get_connection(self, is_async=None):
        """
        Information:
            Get a database connection in either synchronous or asynchronous mode.
            This method doesn't store the connection as an instance attribute.
            Can automatically detect if called from an async context.

        Parameters:
            Input: is_async - Override automatic detection of async context
                   True for asyncpg connection, False for psycopg2 connection,
                   None for automatic detection
            Output: Database connection object (psycopg2 or asyncpg connection)

        Date: 03/06/2025
        Author: TOVY
        """
        # If is_async is None, auto-detect based on calling context
        if is_async is None:
            current_frame = inspect.currentframe()
            calling_frame = inspect.getouterframes(current_frame)[1]
            is_async = inspect.iscoroutinefunction(calling_frame.function)

        try:
            db_config = self._get_db_config()

            if is_async:
                # Asynchronous connection with asyncpg
                connection = await asyncpg.connect(**db_config)
                print(f"Connected asynchronously to database: {db_config['database']}")
                return connection
            else:
                # Synchronous connection with psycopg2
                connection = psycopg2.connect(**db_config)
                print(f"Connected to database: {db_config['database']}")
                return connection

        except Exception as e:
            connection_type = "asynchronous" if is_async else "synchronous"
            print(f"Database {connection_type} connection error: {e}")
            return None

    # Context manager support for synchronous connections
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    # Async context manager support
    async def __aenter__(self):
        await self.connect_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_async()

# Usage examples:

# Example 1: Synchronous connection with context manager
# with DatabaseConnection(config_loader) as db:
#     # Use db.sync_connection and db.sync_cursor here
#     db.sync_cursor.execute("SELECT * FROM table")
#     results = db.sync_cursor.fetchall()

# Example 2: Asynchronous connection with async context manager
# async with DatabaseConnection(config_loader) as db:
#     # Use db.async_connection here
#     results = await db.async_connection.fetch("SELECT * FROM table")

# Example 3: Get a standalone connection (doesn't store in the instance)
# async def example_function():
#     db = DatabaseConnection(config_loader)
#     # Auto-detects that we're in an async context
#     conn = await db.get_connection()
#     try:
#         results = await conn.fetch("SELECT * FROM table")
#         return results
#     finally:
#         await conn.close()