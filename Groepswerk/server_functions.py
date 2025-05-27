import yaml
import sys
import io
import os
import psycopg2
from class_config_loader import ConfigLoader
from insert_data_db_yaml import PLCResourceSync
import head

def run_head_and_capture_output(config_obj, selected_host_value):
    """Capture output from head module execution"""
    buffer = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = sys.stderr = buffer
    try:
        if selected_host_value == "all":
            # For 'all', call it for every host in the yaml_file
            for host in config_obj.get_sftp_hosts():
                host_name = host.get('hostname', host.get('ip_address'))
                print(f"=== {host_name} ===")
                head.run_main_with_host(config_obj, host_name, is_gui_context=True)
                print()
        else:
            head.run_main_with_host(config_obj, selected_host_value, is_gui_context=True)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return buffer.getvalue()

def validate_yaml(yaml_content, save_message):
    """Validate that the provided content is valid YAML."""
    try:
        test_config = yaml.safe_load(yaml_content)
        return test_config
    except Exception as e:
        save_message.set(f"Error: Invalid YAML format - {str(e)}")
        return None

def update_configuration(yaml_content, test_config, config_loader, save_message):
    """Save config to file and update global variables."""
    # Save to file
    config_loader.save_config(yaml_content)
    save_message.set("Configuration saved successfully!")

    # Reinitialize config loader
    config_loader = ConfigLoader("plc.yaml")
    
    return test_config, config_loader

def update_ui_components(config_loader, inputs, selected_resource, resource_buttons_trigger):
    """Update UI components to reflect the new configuration."""
    from shiny import ui
    
    host_options = config_loader.get_host_options()
    
    # Update select component
    ui.update_select("host_select", choices=host_options)

    # Handle resource selection if it no longer exists
    current_host = inputs.host_select()
    current_resource = selected_resource()

    if current_host != "all" and current_resource is not None:
        host_cfg = next((host for host in config_loader.get_sftp_hosts()
                         if host.get('hostname') == current_host or
                         host.get('ip_address') == current_host), None)

        if host_cfg:
            resources = host_cfg.get('resources', [])
            if current_resource not in resources:
                selected_resource.set(None)

    # Trigger resource buttons refresh
    resource_buttons_trigger.set(resource_buttons_trigger() + 1)

async def sync_with_database(config_loader, save_message, session):
    """Synchronize the configuration with the database."""
    try:
        from class_fetch_bits import PLCBitRepositoryAsync
        
        # Update status
        save_message.set("Configuration saved. Synchronizing database...")

        # Force UI update
        await session.send_custom_message("force_update", {})

        # Get database connection
        repo = PLCBitRepositoryAsync(config_loader)
        conn = await repo._get_connection()

        try:
            # Sync database
            plc_sync = PLCResourceSync(config_loader)
            await plc_sync.sync_async(conn)

            # Update status
            save_message.set("Configuration saved and database synchronized successfully!")
        finally:
            await conn.close()

    except ImportError as import_err:
        save_message.set(f"Configuration saved but couldn't import database module: {str(import_err)}")
    except psycopg2.OperationalError as db_conn_err:
        save_message.set(f"Configuration saved but database connection failed: {str(db_conn_err)}")
    except Exception as db_error:
        import traceback
        error_details = traceback.format_exc()
        print(f"Database sync error: {error_details}")
        save_message.set(f"Configuration saved but database sync failed: {str(db_error)}")