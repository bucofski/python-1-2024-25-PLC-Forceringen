import yaml
import sys
import io
import sqlalchemy.exc  # Changed from psycopg2
from Forceringen.util.config_manager import ConfigLoader
from Forceringen.Database.insert_data_db_yaml import PLCResourceSync
from Forceringen.Database.fetch_bits_db import PLCBitRepositoryAsync
from Forceringen.util.unified_db_connection import DatabaseConnection  # Added import
from shiny import reactive, ui
from Forceringen.util import distributor


def run_distributor_and_capture_output(config_obj, selected_host_value):
    """
    Information:
        Captures output from head module execution by temporarily redirecting
        stdout and stderr to a buffer. Handles execution for a single host or
        all hosts based on the selected value.

    Parameters:
        Input: config_obj - ConfigLoader instance with application configuration
              selected_host_value - String specifying the host to process or "all"
        Output: String containing the captured console output

    Date: 03/06/2025
    Author: TOVY
    """
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
                distributor.run_main_with_host(config_obj, host_name, is_gui_context=True)
                print()
        else:
            distributor.run_main_with_host(config_obj, selected_host_value, is_gui_context=True)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return buffer.getvalue()

def validate_yaml(yaml_content, save_message):
    """
    Information:
        Validates that the provided content is valid YAML by attempting to parse it.
        Updates the save_message if validation fails.

    Parameters:
        Input: yaml_content - String containing YAML content to validate
              save_message - Reactive value to update with error messages
        Output: Parsed YAML content as Python object or None if validation fails

    Date: 03/06/2025
    Author: TOVY
    """
    try:
        test_config = yaml.safe_load(yaml_content)
        return test_config
    except Exception as e:
        save_message.set(f"Error: Invalid YAML format - {str(e)}")
        return None

def update_configuration(yaml_content, test_config, config_loader, save_message):
    """
    Information:
        Saves the configuration to file and updates the application's configuration objects.
        Updates the save_message with success status.

    Parameters:
        Input: yaml_content - String containing valid YAML content
              test_config - Parsed YAML configuration
              config_loader - Current ConfigLoader instance
              save_message - Reactive value to update with status messages
        Output: Tuple containing (updated config object, new ConfigLoader instance)

    Date: 03/06/2025
    Author: TOVY
    """
    # Save to file
    config_loader.save_config(yaml_content)
    save_message.set("Configuration saved successfully!")


    # Reinitialize config loader
    config_loader = ConfigLoader(yaml_path=config_loader.yaml_path)

    return test_config, config_loader

def update_ui_components(config_loader, inputs, selected_resource, resource_buttons_trigger):
    """
    Information:
        Updates UI components to reflect the new configuration.
        This includes updating the host select dropdown and handling
        resource selection if a previously selected resource no longer exists.

    Parameters:
        Input: config_loader - Updated ConfigLoader instance
              inputs - Shiny inputs object
              selected_resource - Reactive value for the selected resource
              resource_buttons_trigger - Reactive value to trigger resource buttons refresh

    Date: 03/06/2025
    Author: TOVY
    """

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
        
def create_resource_click_handler(config, inputs, selected_resource, selected_plc, selected_view, plc_bits_data, config_loader):
    """
    Information:
        Creates a reactive effect handler for resource button clicks.
        Tracks click counts to detect only new clicks and prevent duplicate processing.
        When a resource button is clicked, it updates the selected resource and PLC,
        changes the view to "resource", and fetches the bit data for the selected resource.

    Parameters:
        Input: config - Application configuration dictionary
              inputs - Shiny inputs object
              selected_resource - Reactive value for the selected resource
              selected_plc - Reactive value for the selected PLC
              selected_view - Reactive value for the current view mode
              plc_bits_data - Reactive value to store the fetched bit data
              config_loader - ConfigLoader instance for database access
        Output: Reactive effect function that handles resource button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    # Track previous click counts to detect NEW clicks only
    previous_resource_clicks = {}
    
    @reactive.effect
    async def handle_resource_clicks():
        sftp_hosts = config.get('sftp_hosts', [])
        selected_host_val = inputs.host_select()

        # Filter the right host(s)
        if selected_host_val == "all":
            hosts = sftp_hosts
        else:
            hosts = [h for h in sftp_hosts if
                     h.get('hostname') == selected_host_val or h.get('ip_address') == selected_host_val]

        for i, host in enumerate(hosts):
            resources = host.get('resources', [])
            for j, resource in enumerate(resources):
                btn_id = f"resource_{j}"
                if hasattr(inputs, btn_id):
                    btn_input = getattr(inputs, btn_id)
                    current_count = btn_input()
                    
                    # Get previous count for this button (default to 0)
                    prev_count = previous_resource_clicks.get(btn_id, 0)
                    
                    # Only process if there's a NEW click (current > previous)
                    if current_count > prev_count:
                        hostname = host.get("hostname", host.get("ip_address"))
                        selected_resource.set(resource)
                        selected_plc.set(hostname)
                        selected_view.set("resource")
                        print(f"NEW click - Selected resource: {resource} on PLC: {hostname}")
                        print(f"Selected view: {selected_view()}")

                        # --- Fetch plc_bits for this PLC and resource ---
                        repo = PLCBitRepositoryAsync(config_loader)

                        async def get_bits():
                            return await repo.fetch_plc_bits(hostname, resource_name=resource)

                        results = await get_bits()
                        plc_bits_data.set(results)

                        print("Results from plc_bits view:")
                        for row in results:
                            print(row)
                    
                    # Update the stored count
                    previous_resource_clicks[btn_id] = current_count

    return handle_resource_clicks

def create_plc_click_handler(config, inputs, selected_plc, selected_resource, selected_view, plc_bits_data, config_loader):
    """
    Information:
        Creates a reactive effect handler for PLC button clicks.
        Tracks click counts to detect only new clicks and prevent duplicate processing.
        When a PLC button is clicked (only when "all" is selected in the dropdown),
        it updates the selected PLC, clears the selected resource,
        changes the view to "ALL", and fetches all bit data for the selected PLC.

    Parameters:
        Input: config - Application configuration dictionary
              inputs - Shiny inputs object
              selected_plc - Reactive value for the selected PLC
              selected_resource - Reactive value for the selected resource
              selected_view - Reactive value for the current view mode
              plc_bits_data - Reactive value to store the fetched bit data
              config_loader - ConfigLoader instance for database access
        Output: Reactive effect function that handles PLC button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    # Track previous click counts to detect NEW clicks only
    previous_plc_clicks = {}

    @reactive.effect
    async def handle_plc_clicks():

        sftp_hosts = config.get('sftp_hosts', [])

        if inputs.host_select() != "all":
            return  # only active when "all" is selected

        for i, host in enumerate(sftp_hosts):
            btn_id = f"plc_{i}"
            if hasattr(inputs, btn_id):
                btn_input = getattr(inputs, btn_id)
                current_count = btn_input()

                # Get previous count for this button (default to 0)
                prev_count = previous_plc_clicks.get(btn_id, 0)

                # Only process if there's a NEW click (current > previous)
                if current_count > prev_count:
                    hostname = host.get("hostname", host.get("ip_address"))
                    print(f"NEW click - PLC clicked: {hostname}")
                    selected_plc.set(hostname)
                    selected_resource.set(None)

                    selected_view.set("ALL")

                    repo = PLCBitRepositoryAsync(config_loader)

                    async def get_bits():
                        return await repo.fetch_plc_bits(hostname)

                    results = await get_bits()
                    plc_bits_data.set(results)

                    print("Results for PLC:", hostname)
                    for row in results:
                        print(row)
                
                # Update the stored count
                previous_plc_clicks[btn_id] = current_count

    return handle_plc_clicks


def create_detail_click_handler(plc_bits_data, inputs, selected_bit_detail, selected_view, bit_history_data,
                                config_loader, selected_plc):
    """
    Information:
        Creates a reactive effect handler for detail button clicks.
        Tracks click counts to detect only new clicks and prevent duplicate processing.
        When a detail button is clicked, it updates the selected bit detail,
        changes the view to "detail", and fetches the bit history data.

    Parameters:
        Input: plc_bits_data - Reactive value containing the current bit data
              inputs - Shiny inputs object
              selected_bit_detail - Reactive value for the selected bit detail
              selected_view - Reactive value for the current view mode
              bit_history_data - Reactive value to store the bit history data
              config_loader - ConfigLoader instance for database access
              selected_plc - Reactive value for the selected PLC
        Output: Reactive effect function that handles detail button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    # Track previous click counts to detect NEW clicks only
    previous_clicks = {}

    @reactive.effect
    async def handle_detail_clicks():
        data = plc_bits_data()
        for i, item in enumerate(data):
            detail_btn_id = f"detail_btn_{i}"
            if hasattr(inputs, detail_btn_id):
                btn_input = getattr(inputs, detail_btn_id)
                current_count = btn_input()

                # Get previous count for this button (default to 0)
                prev_count = previous_clicks.get(detail_btn_id, 0)

                # Only process if there's a NEW click (current > previous)
                if current_count > prev_count:
                    selected_bit_detail.set(item)
                    selected_view.set("detail")
                    print(f"Detail view for bit: {item.get('bit_number', '')}")

                    # Fetch history data for this bit
                    repository = PLCBitRepositoryAsync(config_loader)
                    history_results = await repository.fetch_bit_history(item, selected_plc())
                    bit_history_data.set(history_results)

                # Update the stored count
                previous_clicks[detail_btn_id] = current_count

    return handle_detail_clicks


def create_save_reason_handler(inputs, plc_bits_data, selected_plc, selected_resource, save_message, config_loader, selected_bit_detail=None, bit_history_data=None):
    """
    Information:
        Creates a unified reactive effect handler for saving reason and forced_by values
        when the Enter key is pressed in either table view or detail view.
        Handles both view contexts based on the provided parameters.

    Parameters:
        Input: inputs - Shiny inputs object
              plc_bits_data - Reactive value containing the current bit data
              selected_plc - Reactive value for the selected PLC
              selected_resource - Reactive value for the selected resource
              save_message - Reactive value to display status messages
              config_loader - ConfigLoader instance for database access
              selected_bit_detail - Optional reactive value for the selected bit detail (detail view)
              bit_history_data - Optional reactive value to store the bit history data (detail view)
        Output: Reactive effect function that handles saving reasons on Enter key

    Date: 08/06/2025
    Author: TOVY
    """

    # Handler for table view (resource/ALL view)
    @reactive.effect
    @reactive.event(inputs.save_reason_triggered)
    async def handle_save_reason_table():
        await _save_reason_common("table", inputs.save_reason_triggered())

    # Handler for detail view
    @reactive.effect
    @reactive.event(inputs.save_reason_detail_triggered)
    async def handle_save_reason_detail():
        await _save_reason_common("detail", inputs.save_reason_detail_triggered())

    async def _save_reason_common(view_type, trigger_data):
        """Common logic for saving reasons in both views"""
        if not trigger_data:
            return

        # ✅ Extra defensieve check voor view type
        if view_type == "detail":
            bit_data = selected_bit_detail()
            if not bit_data:
                print("Warning: Save reason triggered for detail view but no bit selected - ignoring")
                return  # ✅ Gewoon returnen zonder error message te zetten
    
        # Get data based on view type
        if view_type == "table":
            # Table view logic
            index = int(trigger_data.get('index', -1))
            reason_text = trigger_data.get('reasonValue', '')
            melding_text = trigger_data.get('meldingValue', '')  # Add melding extraction
            forced_text = trigger_data.get('forcedValue', '')

            data = plc_bits_data()
            if not data or index < 0 or index >= len(data):
                print("Warning: Save reason triggered for table view but no valid data - ignoring")
                return

            record = data[index]
            plc_name = selected_plc.get()
            resource_name = selected_resource.get()
            bit_number = record.get('bit_number')

        else:  # detail view
            # Detail view logic
            reason_text = trigger_data.get('reasonValue', '')
            melding_text = trigger_data.get('meldingValue', '')
            forced_text = trigger_data.get('forcedValue', '')

            bit_data = selected_bit_detail()
            if not bit_data:
                print("Warning: Save reason triggered for detail view but no bit selected - ignoring")
                return

            plc_name = bit_data.get('PLC') or selected_plc()
            resource_name = bit_data.get('resource') or selected_resource()
            bit_number = bit_data.get('bit_number')
            record = bit_data

        print(f"Saving reason in {view_type} view for bit {bit_number} on PLC {plc_name} resource {resource_name}...")

        try:
            # Create DB connection using unified connection
            db_connection = DatabaseConnection(config_loader)
            conn = await db_connection.get_connection(is_async=True)

            try:
                # Update the reason in the database with SQL Server syntax - FIXED PARAMETER ORDER
                result = await conn.execute(
                    "EXEC insert_force_reason :plc_name, :resource_name, :bit_number, :reason_text, :melding_text, :forced_text",
                    {
                        "plc_name": plc_name,
                        "resource_name": resource_name,
                        "bit_number": bit_number,
                        "reason_text": reason_text,
                        "melding_text": melding_text,
                        "forced_text": forced_text
                    }
                )

                # Check result and update status
                if result:
                    save_message.set(f"Reason saved for bit {bit_number}")
                    print(f"Updated reason for bit {bit_number} to: {reason_text}")
                    print(f"Updated melding for bit {bit_number} to: {melding_text}")
                    print(f"Updated forced_by for bit {bit_number} to: {forced_text}")

                    # Update local data based on view type
                    if view_type == "table":
                        # Update table data
                        record['reason'] = reason_text
                        record['melding'] = melding_text  # Add melding update
                        record['forced_by'] = forced_text
                        new_data = data.copy()
                        new_data[index] = record
                        plc_bits_data.set(new_data)
                    else:  # detail view
                        # Update detail data
                        updated_bit_data = record.copy()
                        updated_bit_data['reason'] = reason_text
                        updated_bit_data['melding'] = melding_text  # Add melding update
                        updated_bit_data['forced_by'] = forced_text
                        selected_bit_detail.set(updated_bit_data)

                        # Refresh history data if available
                        if bit_history_data is not None:
                            repository = PLCBitRepositoryAsync(config_loader)
                            history_results = await repository.fetch_bit_history(updated_bit_data, selected_plc())
                            bit_history_data.set(history_results)

                else:
                    save_message.set(f"Failed to save reason for bit {bit_number}")
            finally:
                await conn.disconnect()

        except Exception as e:
            save_message.set(f"Error: {str(e)}")
            print(f"Database error: {str(e)}")

    return handle_save_reason_table, handle_save_reason_detail

def create_back_button_handler(inputs, selected_resource, selected_view, plc_bits_data, config_loader, selected_plc):
    """
    Information:
        Creates a reactive effect handler for the back button in the detail view.
        When clicked, it returns to either the resource view or the PLC view,
        depending on the current context, and refreshes the bit data.

    Parameters:
        Input: inputs - Shiny inputs object
              selected_resource - Reactive value for the selected resource
              selected_view - Reactive value for the current view mode
              plc_bits_data - Reactive value to store the fetched bit data
              config_loader - ConfigLoader instance for database access
              selected_plc - Reactive value for the selected PLC
        Output: Reactive effect function that handles back button clicks

    Date: 03/06/2025
    Author: TOVY
    """

    @reactive.effect
    @reactive.event(inputs.back_to_list)
    async def handle_back_button():
        # Return to the appropriate view based on what was selected
        if selected_resource():
            selected_view.set("resource")
            # Refresh the resource data
            repo = PLCBitRepositoryAsync(config_loader)
            results = await repo.fetch_plc_bits(selected_plc(), resource_name=selected_resource())
            plc_bits_data.set(results)
            print(f"Refreshed data for resource {selected_resource()} on PLC {selected_plc()}")
        else:
            selected_view.set("ALL")
            # Refresh the PLC data
            repo = PLCBitRepositoryAsync(config_loader)
            results = await repo.fetch_plc_bits(selected_plc())
            plc_bits_data.set(results)
            print(f"Refreshed data for PLC {selected_plc()}")

    return handle_back_button