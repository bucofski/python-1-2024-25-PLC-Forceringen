import yaml
import sys
import io
import psycopg2
from class_config_loader import ConfigLoader
from insert_data_db_yaml import PLCResourceSync
from class_fetch_bits import PLCBitRepositoryAsync
from shiny import reactive, ui, render
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

async def fetch_bit_history(bit_data, config_loader, selected_plc, bit_history_data):
    """Fetch the last 5 force reasons for the selected bit"""
    try:
        repo = PLCBitRepositoryAsync(config_loader)
        conn = await repo._get_connection()

        try:
            plc_name = bit_data.get('PLC') or selected_plc()
            resource_name = bit_data.get('resource')
            bit_number = bit_data.get('bit_number')

            # Query the last_5_force_reasons_per_bit view
            history_query = """
                SELECT *
                FROM last_5_force_reasons_per_bit
                WHERE PLC = $1
                  AND resource = $2
                  AND bit_number = $3
                ORDER BY forced_at DESC;
            """

            history_results = await conn.fetch(history_query, plc_name, resource_name, bit_number)

            # Convert to list of dicts
            history_data = []
            for row in history_results:
                history_data.append(dict(row))

            bit_history_data.set(history_data)
            print(f"Fetched {len(history_data)} history records for bit {bit_number}")

        finally:
            await conn.close()

    except Exception as e:
        print(f"Error fetching bit history: {str(e)}")
        bit_history_data.set([])

def create_resource_click_handler(config, inputs, selected_resource, selected_plc, selected_view, plc_bits_data, config_loader):
    """Create handler for resource button clicks"""
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
                    if btn_input() > 0:
                        hostname = host.get("hostname", host.get("ip_address"))
                        selected_resource.set(resource)
                        selected_plc.set(hostname)
                        selected_view.set("resource")
                        print(f"Selected resource: {resource} on PLC: {hostname}")
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

    return handle_resource_clicks

def create_plc_click_handler(config, inputs, selected_plc, selected_resource, selected_view, plc_bits_data, config_loader):
    """Create handler for PLC button clicks"""
    @reactive.effect
    async def handle_plc_clicks():
        sftp_hosts = config.get('sftp_hosts', [])

        if inputs.host_select() != "all":
            return  # only active when "all" is selected

        for i, host in enumerate(sftp_hosts):
            btn_id = f"plc_{i}"
            if hasattr(inputs, btn_id):
                btn_input = getattr(inputs, btn_id)
                if btn_input() > 0:
                    hostname = host.get("hostname", host.get("ip_address"))
                    print(f"PLC clicked: {hostname}")
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

    return handle_plc_clicks

def create_detail_click_handler(plc_bits_data, inputs, selected_bit_detail, selected_view, bit_history_data, config_loader, selected_plc):
    """Create handler for detail button clicks"""
    @reactive.effect
    async def handle_detail_clicks():
        data = plc_bits_data()
        for i, item in enumerate(data):
            detail_btn_id = f"detail_btn_{i}"
            if hasattr(inputs, detail_btn_id):
                btn_input = getattr(inputs, detail_btn_id)
                if btn_input() > 0:
                    selected_bit_detail.set(item)
                    selected_view.set("detail")
                    print(f"Detail view for bit: {item.get('bit_number', '')}")

                    # Fetch history data for this bit
                    await fetch_bit_history(item, config_loader, selected_plc, bit_history_data)

    return handle_detail_clicks

def create_save_reason_handler(inputs, plc_bits_data, selected_plc, selected_resource, save_message, config_loader):
    """Create handler for saving reasons on Enter key"""
    @reactive.effect
    @reactive.event(inputs.save_reason_triggered)
    async def handle_save_reason_on_enter():
        trigger_data = inputs.save_reason_triggered()
        if not trigger_data:
            return

        # Get data from the triggered event
        index = int(trigger_data.get('index', -1))
        reason_text = trigger_data.get('reasonValue', '')
        forced_text = trigger_data.get('forcedValue', '')

        # Get the data
        data = plc_bits_data()
        if not data or index < 0 or index >= len(data):
            save_message.set("Error: Invalid data index")
            return

        # Get the record that needs updating
        record = data[index]
        plc_name = selected_plc.get()
        resource_name = selected_resource.get()
        bit_number = record.get('bit_number')
        print(f"Saving reason for bit {bit_number} on PLC {plc_name} resource {resource_name}...")
        try:
            # Create DB connection
            repo = PLCBitRepositoryAsync(config_loader)
            conn = await repo._get_connection()

            try:
                # Update the reason in the database
                result = await conn.fetchrow(
                    "SELECT * FROM insert_force_reason($1, $2, $3, $4, $5)",
                    plc_name, resource_name, bit_number, reason_text, forced_text
                )
                # Check result and update status
                if result:
                    save_message.set(f"Reason saved for bit {bit_number}")
                    print(f"Updated reason for bit {bit_number} to: {reason_text}")
                    print(f"Updated forced_by for bit {bit_number} to: {forced_text}")

                    # Update the local data to reflect changes
                    record['reason'] = reason_text
                    record['forced_by'] = forced_text
                    new_data = data.copy()
                    new_data[index] = record
                    plc_bits_data.set(new_data)
                else:
                    save_message.set(f"Failed to save reason for bit {bit_number}")
            finally:
                await conn.close()

        except Exception as e:
            save_message.set(f"Error: {str(e)}")
            print(f"Database error: {str(e)}")

    return handle_save_reason_on_enter

def create_back_button_handler(inputs, selected_resource, selected_view):
    """Create handler for back button click"""
    @reactive.effect
    @reactive.event(inputs.back_to_list)
    def handle_back_button():
        # Return to the appropriate view based on what was selected
        if selected_resource():
            selected_view.set("resource")
        else:
            selected_view.set("ALL")

    return handle_back_button