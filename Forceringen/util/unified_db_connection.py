import inspect
#import asyncio
from sqlalchemy import create_engine, text
#from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
#from sqlalchemy.orm import sessionmaker
import aioodbc


class DatabaseConnection:
    """
    Information:
        Unified database connection class that provides both synchronous and asynchronous
        database connections with a consistent interface. Supports context managers,
        automatic async detection, and connection management for SQL Server using SQLAlchemy + aioodbc.

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
        self.sync_engine = None
        self.sync_connection = None
        self.async_engine = None
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
            "server": db_config.get("host", "localhost"),
            "port": db_config.get("port", 1433),
            "database": db_config.get("database"),
            "user": db_config.get("user"),
            "password": db_config.get("password"),
            "driver": db_config.get("driver", "ODBC Driver 17 for SQL Server")
        }

    def _build_sync_connection_string(self, db_config):
        """
        Information:
            Build synchronous connection string for SQL Server using SQLAlchemy.
            
        Parameters:
            Input: db_config - Dictionary with database connection parameters
            Output: Connection string for SQLAlchemy synchronous engine

        Date: 03/06/2025
        Author: TOVY
        """
        return f"mssql+pyodbc://{db_config['user']}:{db_config['password']}@{db_config['server']}:{db_config['port']}/{db_config['database']}?driver={db_config['driver'].replace(' ', '+')}"

    def _build_async_connection_string(self, db_config):
        """
        Information:
            Build asynchronous connection string for SQL Server using aioodbc.
            
        Parameters:
            Input: db_config - Dictionary with database connection parameters
            Output: Connection string for aioodbc

        Date: 03/06/2025
        Author: TOVY
        """
        return f"DRIVER={{{db_config['driver']}}};SERVER={db_config['server']},{db_config['port']};DATABASE={db_config['database']};UID={db_config['user']};PWD={db_config['password']}"

    def connect(self):
        """
        Information:
            Establish a synchronous connection to the SQL Server database using SQLAlchemy.
            Stores the engine and connection as instance attributes.
            Provides feedback about connection status.

        Parameters:
            Output: Boolean indicating connection success or failure

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            db_config = self._get_db_config()
            connection_string = self._build_sync_connection_string(db_config)
            
            self.sync_engine = create_engine(connection_string, echo=False)
            self.sync_connection = self.sync_engine.connect()
            
            print(f"Connected to SQL Server database: {db_config['database']}")
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    async def connect_async(self):
        """
        Information:
            Establish an asynchronous connection to the SQL Server database using aioodbc.
            Stores the connection as an instance attribute.
            Provides feedback about connection status.

        Parameters:
            Output: Boolean indicating connection success or failure

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            db_config = self._get_db_config()
            connection_string = self._build_async_connection_string(db_config)
            
            self.async_connection = await aioodbc.connect(dsn=connection_string)
            
            print(f"Connected asynchronously to SQL Server database: {db_config['database']}")
            return True
        except Exception as e:
            print(f"Asynchronous database connection error: {e}")
            return False

    def disconnect(self):
        """
        Information:
            Close the synchronous database connection and engine.
            Resets instance attributes to None after closing.
            Provides feedback when connection is closed.

        Date: 03/06/2025
        Author: TOVY
        """
        if self.sync_connection:
            self.sync_connection.close()
            self.sync_connection = None
        if self.sync_engine:
            self.sync_engine.dispose()
            self.sync_engine = None
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
                   True for aioodbc connection, False for SQLAlchemy connection,
                   None for automatic detection
            Output: Database connection object (SQLAlchemy or aioodbc connection)

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
                # Asynchronous connection with aioodbc
                connection_string = self._build_async_connection_string(db_config)
                connection = await aioodbc.connect(dsn=connection_string)
                print(f"Connected asynchronously to SQL Server database: {db_config['database']}")
                return DatabaseConnectionWrapper(connection, is_async=True)
            else:
                # Synchronous connection with SQLAlchemy
                connection_string = self._build_sync_connection_string(db_config)
                engine = create_engine(connection_string, echo=False)
                connection = engine.connect()
                print(f"Connected to SQL Server database: {db_config['database']}")
                return DatabaseConnectionWrapper(connection, is_async=False, engine=engine)

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


class DatabaseConnectionWrapper:
    """
    Information:
        Wrapper class that provides a unified interface for both SQLAlchemy and aioodbc connections.
        Standardizes method names and behavior between sync and async connections.

    Date: 03/06/2025
    Author: TOVY
    """
    
    def __init__(self, connection, is_async=False, engine=None):
        """
        Information:
            Initialize the wrapper with a connection object.
            
        Parameters:
            Input: connection - SQLAlchemy or aioodbc connection
                  is_async - Boolean indicating if this is an async connection
                  engine - SQLAlchemy engine (for sync connections only)

        Date: 03/06/2025
        Author: TOVY
        """
        self.connection = connection
        self.is_async = is_async
        self.engine = engine

    async def fetch_all(self, query, parameters=None):
        """
        Information:
            Execute a SELECT query and return all results.
            Works with both sync and async connections.

        Parameters:
            Input: query - SQL query string
                  parameters - Dictionary of query parameters
            Output: List of result rows as dictionaries

        Date: 03/06/2025
        Author: TOVY
        """
        if self.is_async:
            cursor = await self.connection.cursor()
            try:
                if parameters:
                    # Convert named parameters to positional for aioodbc
                    param_values = list(parameters.values())
                    query_converted = query
                    for key, value in parameters.items():
                        query_converted = query_converted.replace(f":{key}", "?")
                    await cursor.execute(query_converted, param_values)
                else:
                    await cursor.execute(query)
                
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            finally:
                await cursor.close()
        else:
            if parameters:
                result = self.connection.execute(text(query), parameters)
            else:
                result = self.connection.execute(text(query))
            return [dict(row._mapping) for row in result]

    async def fetch_one(self, query, parameters=None):
        """
        Information:
            Execute a SELECT query and return the first result.
            Works with both sync and async connections.

        Parameters:
            Input: query - SQL query string
                  parameters - Dictionary of query parameters
            Output: Single result row as dictionary or None

        Date: 03/06/2025
        Author: TOVY
        """
        if self.is_async:
            cursor = await self.connection.cursor()
            try:
                if parameters:
                    param_values = list(parameters.values())
                    query_converted = query
                    for key, value in parameters.items():
                        query_converted = query_converted.replace(f":{key}", "?")
                    await cursor.execute(query_converted, param_values)
                else:
                    await cursor.execute(query)
                
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
            finally:
                await cursor.close()
        else:
            if parameters:
                result = self.connection.execute(text(query), parameters)
            else:
                result = self.connection.execute(text(query))
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def execute(self, query, parameters=None):
        """
        Information:
            Execute an INSERT, UPDATE, or DELETE query.
            Works with both sync and async connections.

        Parameters:
            Input: query - SQL query string
                  parameters - Dictionary of query parameters
            Output: Number of affected rows

        Date: 03/06/2025
        Author: TOVY
        """
        if self.is_async:
            cursor = await self.connection.cursor()
            try:
                if parameters:
                    param_values = list(parameters.values())
                    query_converted = query
                    for key, value in parameters.items():
                        query_converted = query_converted.replace(f":{key}", "?")
                    await cursor.execute(query_converted, param_values)
                else:
                    await cursor.execute(query)
                
                await self.connection.commit()
                return cursor.rowcount
            finally:
                await cursor.close()
        else:
            if parameters:
                result = self.connection.execute(text(query), parameters)
            else:
                result = self.connection.execute(text(query))
            self.connection.commit()
            return result.rowcount

    async def disconnect(self):
        """
        Information:
            Close the database connection.
            Works with both sync and async connections.

        Date: 03/06/2025
        Author: TOVY
        """
        if self.is_async:
            await self.connection.close()
        else:
            self.connection.close()
            if self.engine:
                self.engine.dispose()


# Usage examples:

# Example 1: Synchronous connection with context manager
# with DatabaseConnection(config_loader) as db:
#     result = db.sync_connection.execute(text("SELECT * FROM table"))
#     results = [dict(row._mapping) for row in result]

# Example 2: Asynchronous connection with async context manager
# async with DatabaseConnection(config_loader) as db:
#     cursor = await db.async_connection.cursor()
#     await cursor.execute("SELECT * FROM table")
#     results = await cursor.fetchall()

# Example 3: Get a standalone connection (doesn't store in the instance)
# async def example_function():
#     db = DatabaseConnection(config_loader)
#     conn = await db.get_connection()
#     try:
#         results = await conn.fetch_all("SELECT * FROM table")
#         return results
#     finally:
#         await conn.disconnect()