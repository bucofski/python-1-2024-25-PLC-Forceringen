import sqlalchemy.exc
from Forceringen.util.config_manager import ConfigLoader
from Forceringen.Database.insert_data_db_yaml import PLCResourceSync


async def sync_with_database(config_loader, save_message, session):
    """
    Information:
        Synchronizes the configuration with the database asynchronously.
        Updates save_message with status updates and error messages.
        Handles various error conditions including import errors and
        database connection failures.

    Parameters:
        Input: config_loader - Updated ConfigLoader instance
              save_message - Reactive value for status messages
              session - Shiny session object for UI updates

    Date: 03/06/2025
    Author: TOVY
    """
    try:
        # Update status
        save_message.set("Configuration saved. Synchronizing database...")

        # Force UI update
        await session.send_custom_message("force_update", {})

        # Sync database - PLCResourceSync creates its own connection
        plc_sync = PLCResourceSync(config_loader)
        await plc_sync.sync_async()  # Remove the conn parameter

        # Update status
        save_message.set("Configuration saved and database synchronized successfully!")

    except ImportError as import_err:
        save_message.set(f"Configuration saved but couldn't import database module: {str(import_err)}")
    except sqlalchemy.exc.OperationalError as db_conn_err:
        save_message.set(f"Configuration saved but database connection failed: {str(db_conn_err)}")
    except Exception as db_error:
        import traceback
        error_details = traceback.format_exc()
        print(f"Database sync error: {error_details}")
        save_message.set(f"Configuration saved but database sync failed: {str(db_error)}")