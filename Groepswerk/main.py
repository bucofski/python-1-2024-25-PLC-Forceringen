from class_fetch_bits import PLCBitRepositoryAsync
from class_config_loader import ConfigLoader
from shiny import App, ui, render, reactive
from ui_components import create_app_ui, create_resource_buttons_ui, COLOR
from server_functions import (
    run_head_and_capture_output, validate_yaml, update_configuration,
    update_ui_components, sync_with_database
)
import os

# Read host options from YAML
script_dir = os.path.dirname(os.path.abspath(__file__))
yaml_path = os.path.join(script_dir, "..", "Groepswerk", "plc.yaml")

try:
    config_loader = ConfigLoader("plc.yaml")
    config = config_loader.config  # Store for backward compatibility
    host_options = config_loader.get_host_options()
except FileNotFoundError:
    raise RuntimeError(
        f"YAML config file not found: {yaml_path}\n"
        "Please make sure 'plc.yaml' exists in the group work folder next to this script."
    )

# Create the UI
app_ui = create_app_ui(host_options)


def server(inputs, outputs, session):
    # Reactive values
    assert session
    terminal_text = reactive.Value("")
    selected_view = reactive.Value("output")  # "output" or "Config"
    selected_resource = reactive.Value(None)
    selected_plc = reactive.Value(None)  # Only when used "all"
    plc_bits_data = reactive.Value([])
    resource_buttons_trigger = reactive.Value(0)
    save_message = reactive.Value("")

    # View-switching logic
    @reactive.effect
    @reactive.event(inputs.view_output)
    def _():
        selected_view.set("output")
        print("Selected view is:", selected_view())

    @reactive.effect
    @reactive.event(inputs.view_config)
    def _():
        selected_view.set("Config")
        print("Selected view is:", selected_view())

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

    @outputs()
    @render.text
    def selected_host():
        return f"Selected Host: {inputs.host_select()}"

    @outputs()
    @render.text
    def terminal_output():
        return terminal_text()

    @reactive.effect
    @reactive.event(inputs.start_btn)
    def on_start():
        selected_host_value = inputs.host_select()
        captured_output = run_head_and_capture_output(config_loader, selected_host_value)
        terminal_text.set(captured_output or "[No output produced]")

    @outputs()
    @render.ui
    def resource_buttons():
        # Make this output depend on the trigger
        resource_buttons_trigger()

        # BELANGRIJKE FIX: Gebruik de globale config variabele
        return create_resource_buttons_ui(config, inputs, selected_resource, selected_plc)

    @outputs()
    @render.ui
    def main_panel():
        if selected_view() == "output":
            return ui.tags.div(
                ui.output_text("selected_host"),
                ui.tags.h2("Output"),
                ui.output_text_verbatim("terminal_output", placeholder=True)
            )
        elif selected_view() == "Config":
            # Load and display the content of plc.yaml for editing
            with open(yaml_path, "r") as file:
                yaml_content = file.read()

            return ui.tags.div(
                ui.tags.h2("PLC Configuration"),
                ui.tags.div(
                    ui.tags.label(
                        "Edit PLC Configuration:",
                        **{"for": "yaml_editor"},
                        style="display: block; margin-bottom: 8px; font-size: 1.1rem;"
                    ),
                    ui.input_text_area(
                        "yaml_editor",
                        label=None,
                        value=yaml_content,
                        height="600px",
                        width="800px",
                        resize="both"
                    ),
                    style="display: flex; flex-direction: column; align-items: center; margin: 0 auto;"
                ),
                ui.tags.div(
                    ui.input_action_button(
                        "save_config",
                        "Save Changes",
                        class_="button button1",
                        style="margin-top: 16px; padding: 10px 20px;"
                    ),
                    ui.tags.div(
                        ui.output_text("save_status_output"),
                        style="margin-top: 12px; font-weight: bold;"
                    ),
                    style="display: flex; flex-direction: column; align-items: center; margin-top: 16px;"
                ),
                style="width: 800px; margin: 0 auto; text-align: center;"
            )

        elif selected_view() == "resource":
            # Get the data
            data = plc_bits_data()

            if not data:
                return ui.tags.div(
                    ui.tags.h2(f"Resource: {selected_resource()}"),
                    ui.tags.p("No data available for this resource.")
                )

            # Create column headers
            headers = [
                "Bit Number", "KKS",
                "Comment", "Second Comment", "Value",
                "Forced At", "forced by", "Reason"
            ]

            # Create the table header row
            header_cells = [ui.tags.th(header) for header in headers]
            header_row = ui.tags.tr(*header_cells)

            # Create table rows for each data item
            rows = []
            for i, item in enumerate(data):
                # Format datetime for display
                forced_at = item.get('forced_at')
                if forced_at:
                    forced_at_str = forced_at.strftime("%d-%m-%Y")
                else:
                    forced_at_str = ""

                # Format None values as empty strings
                comment = item.get('comment', '')
                if comment == 'None':
                    comment = ''

                second_comment = item.get('second_comment', '')
                if second_comment == 'None':
                    second_comment = ''

                forced_by = item.get('forced_by', '')
                if forced_by == 'None':
                    forced_by = ''

                reason = item.get('reason', '')
                if reason == 'None':
                    reason = ''

                # Create row with cells
                row_class = "force-active" if item.get('force_active') else ""

                # Create unique ID for reason input field based on row index
                reason_id = f"reason_input_{i}"
                forced_id = f"forced_input_{i}"

                cells = [
                    ui.tags.td(item.get('bit_number', '')),
                    ui.tags.td(item.get('kks', '')),
                    ui.tags.td(comment),
                    ui.tags.td(second_comment),
                    ui.tags.td(item.get('value', '')),
                    ui.tags.td(forced_at_str),
                    ui.tags.td(ui.input_text(forced_id, "", value=forced_by, placeholder="Enter user...")),
                    ui.tags.td(ui.input_text(reason_id, "", value=reason, placeholder="Enter reason..."))
                ]

                rows.append(ui.tags.tr(*cells, class_=row_class, id=f"bit_row_{i}"))

            # Build the complete table
            table = ui.tags.table(
                ui.tags.thead(header_row),
                ui.tags.tbody(*rows),
                class_="data-grid"
            )

            # Add CSS for styling the reason input field
            input_css = ui.tags.style("""
        input[type="text"] {
            width: 100%;
            padding: 6px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        input[type="text"]:focus {
            border-color: #FB4400;
            outline: none;
            box-shadow: 0 0 0 2px rgba(251, 68, 0, 0.25);
        }
    """)

            # Return the final UI component
            return ui.tags.div(
                ui.tags.h2(f"Resource: {selected_resource()} on PLC: {selected_plc()}"),
                input_css,
                ui.tags.div(
                    table,
                    class_="data-grid-container"
                ),
                ui.output_text("save_status")
            )

        elif selected_view() == "ALL":
            # Get the data
            data = plc_bits_data()

            if not data:
                return ui.tags.div(
                    ui.tags.h2(f"Resource: {selected_resource()}"),
                    ui.tags.p("No data available for this resource.")
                )

            # Create column headers
            headers = [
                "resource", "Bit Number", "KKS",
                "Comment", "Second Comment", "Value",
                "Forced At", "forced by"
            ]

            # Create the table header row
            header_cells_plc = [ui.tags.th(header) for header in headers]
            header_row = ui.tags.tr(*header_cells_plc)

            # Create table rows for each data item
            rows = []
            for i, item in enumerate(data):
                # Format datetime for display
                forced_at = item.get('forced_at')
                if forced_at:
                    forced_at_str = forced_at.strftime("%d-%m-%Y")
                else:
                    forced_at_str = ""

                # Format None values as empty strings
                comment = item.get('comment', '')
                if comment == 'None':
                    comment = ''

                second_comment = item.get('second_comment', '')
                if second_comment == 'None':
                    second_comment = ''

                # Create row with cells
                row_class = "force-active" if item.get('force_active') else ""

                cells = [
                    ui.tags.td(item.get('resource', '')),
                    ui.tags.td(item.get('bit_number', '')),
                    ui.tags.td(item.get('kks', '')),
                    ui.tags.td(comment),
                    ui.tags.td(second_comment),
                    ui.tags.td(item.get('value', '')),
                    ui.tags.td(forced_at_str),
                    ui.tags.td(item.get('forced_by', ''))
                ]

                rows.append(ui.tags.tr(*cells, class_=row_class, id=f"bit_row_{i}"))

            # Build the complete table
            table = ui.tags.table(
                ui.tags.thead(header_row),
                ui.tags.tbody(*rows),
                class_="data-grid"
            )

            # Add CSS for styling the reason input field
            input_css = ui.tags.style("""
                input[type="text"] {
                    width: 100%;
                    padding: 6px 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    box-sizing: border-box;
                }
                input[type="text"]:focus {
                    border-color: #FB4400;
                    outline: none;
                    box-shadow: 0 0 0 2px rgba(251, 68, 0, 0.25);
                }
            """)

            # Return the final UI component
            return ui.tags.div(
                ui.tags.h2(f"PLC: {selected_plc()}"),
                input_css,
                ui.tags.div(
                    table,
                    class_="data-grid-container"
                ),
                ui.output_text("save_status")
            )

        return None

    # Update config save handler to use imported functions
    @reactive.effect
    @reactive.event(inputs.save_config)
    async def save_yaml_config():
        """Handle YAML configuration saving and database synchronization."""
        global config, config_loader, host_options

        try:
            # Step 1: Get and validate YAML content
            yaml_content = inputs.yaml_editor()
            test_config = validate_yaml(yaml_content, save_message)
            if not test_config:
                return

            # Step 2: Save configuration and update global state
            config, config_loader = update_configuration(yaml_content, test_config, config_loader, save_message)
            host_options = config_loader.get_host_options()

            # Step 3: Update UI components
            update_ui_components(config_loader, inputs, selected_resource, resource_buttons_trigger)

            # Step 4: Synchronize with database
            await sync_with_database(config_loader, save_message, session)

            # Set success status
            save_message.set("Configuration saved successfully!")

        except Exception as e:
            save_message.set(f"Error saving file: {str(e)}")

    @outputs()
    @render.text
    def save_status_output():
        return save_message()

    # Add these inside the server function to handle saving reasons on Enter key
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

    @outputs()
    @render.text
    def save_status():
        message = save_message()
        # Clear the message after 3 seconds
        if message:
            ui.notification_show(message, duration=3)
            save_message.set("")
        return ""


app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app

    run_app(app)