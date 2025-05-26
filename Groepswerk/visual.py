from class_fetch_bits import PLCBitRepositoryAsync
from insert_data_db_yaml import PLCResourceSync
from class_config_loader import ConfigLoader
from shiny import App, ui, render, reactive
import psycopg2
import head
import yaml
import sys
import os
import io

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

COLOR = "#FB4400"

# Add this to your UI section near other JavaScript code
enter_key_js = ui.tags.script("""
document.addEventListener('DOMContentLoaded', function() {
    // Delegate event listener for all current and future text inputs
    document.addEventListener('keydown', function(event) {
        const target = event.target;
        
        // Check if it's a reason input field and Enter was pressed
        if (target.id && target.id.startsWith('reason_input_') && event.key === 'Enter') {
            event.preventDefault();
            
            // Get the index from the input ID
            const index = target.id.split('_')[2];
            
            // Get the value from the forced_by field too
            const forcedInput = document.getElementById('forced_input_' + index);
            const forcedValue = forcedInput ? forcedInput.value : '';
            
            // Trigger a custom event that Shiny can listen for
            Shiny.setInputValue('save_reason_triggered', {
                index: index,
                reasonValue: target.value,
                forcedValue: forcedValue,
                timestamp: new Date().getTime()  // Force reactivity on repeated saves
            });
        }
    });
});
""")

# Add this to your app_ui near the end, before the final style
app_ui = ui.tags.div(
    # CSS for sidebar and transitions - updated with font
    ui.tags.style(
        f"""
        @font-face {{
            font-family: 'VAGRoundedLight';
            src: local('VAG Rounded Light'), local('VAGRoundedLight');
            font-weight: 300;
            font-style: normal;
        }}
        body, .sidebar, .main-panel, .sidebar-toggle, .button, .button1, h1, h2, select, label, p {{
            font-family: 'VAGRoundedLight', 'VAG Rounded Light', 'Arial Rounded MT Bold', Arial, sans-serif !important;
        }}
        .sidebar {{
            background: {COLOR};
            padding: 20px; color: white;
            min-height: 100vh;
            width: 220px; box-sizing: border-box;
            position: fixed; top: 70px; left: 0;
            transition: transform 0.2s cubic-bezier(.42,0,.58,1);
            text-align: center;
            z-index: 110;
        }}
        .sidebar.collapsed {{
            transform: translateX(-220px);
        }}
        .main-panel {{
            margin-left: 240px;
            padding: 90px 30px 30px 30px;
            transition: margin-left 0.2s cubic-bezier(.42,0,.58,1);
        }}
        .sidebar.collapsed + .main-panel {{
            margin-left: 20px;
        }}
        .sidebar-toggle {{
            position: fixed;
            left: 10px; top: 20px; z-index: 120;
            background-color: {COLOR};
            color: white; border: none;
            border-radius: 50%;
            width: 36px; height: 36px;
            cursor: pointer; font-size: 18px;
            outline: none;
            display: flex; align-items: center; justify-content: center;
            box-shadow:
            0 4px 12px 2px rgba(0,0,0,0.18),
            0 1px 4px 0 rgba(0,0,0,0.10),
            0 0 0 3px rgba(255,56,1,0.10);
            transition: box-shadow 0.3s;

        }}
        """
    ),
    # Add the CSS for the button appearance
    ui.tags.style(
        """
        .button {
              border: none;
              color: white;
              padding: 16px 32px;
              text-align: center;
              text-decoration: none;
              display: inline-block;
              font-size: 16px;
              margin: 4px 2px;
              transition-duration: 0.4s;
              cursor: pointer;
              font-family: 'VAGRoundedLight';
              box-shadow:
              0 8px 32px 4px rgba(0,0,0,0.40),
              0 2px 8px 1px rgba(0,0,0,0.24),
              0 0 0 6px rgba(255,56,1,0.12);
              transition: box-shadow 0.3s;
        }
        .button1 {
          background-color: white;
          color: black;
          border: 2px solid #90D5FF;
          font-family: 'VAGRoundedLight';
        }
        .button1.selected {
          background-color: #90D5FF;
          color: white;
        }
        .button1:hover {
          background-color: #90D5FF;
          color: white;
        }
        """
    ),
    # ...OTHER STYLES...
    ui.tags.style("""
        #host_select-label, select#host_select {
            font-size: 1.25rem;
            padding: 10px;
            height: 48px;
            width: 90%;

            font-family: 'VAGRoundedLight';
        }
    """),
    ui.tags.style(
        f"""
        h1 {{
            text-shadow:
                0 4px 24px rgba(0,0,0,0.45),
                0 1.5px 0 rgba(0,0,0,0.28),
                0 0 12px {COLOR}55;
        }}
        """
    ),
    # Top bar (centered)
    ui.tags.div(
        ui.tags.h1(
            "PLC Forceringen",
            style="margin: 0; color: white; font-size: 2rem; text-align: center;"
        ),
        style=f"""
            width: 100vw;
            background: {COLOR};
            color: white;
            padding: 0; margin: 0;
            box-sizing: border-box;
            position: fixed; top: 0; left: 0;
            height: 70px;
            display: flex; justify-content: center; align-items: center;
            z-index: 100;
        """
    ),
    # Sidebar toggle button
    ui.tags.button("☰", id="sidebarToggle", class_="sidebar-toggle"),
    # Page layout: sidebar plus main area
    ui.tags.div(
        # Sidebar
        ui.tags.div(
            ui.tags.div(
                ui.input_select(
                    "host_select",
                    "Select PLC:",
                    choices=host_options,
                ),
                style="margin-bottom: 32px;"
            ),
            # Refreshes buttons stays at the very top (right after host select)
            ui.tags.div(
                ui.input_action_button(
                    "start_btn", "Get Forcing", class_="button button1",
                    style="width:90%; margin-bottom:8px;"
                ),
            ),
            # Dynamic resource/PLC buttons come next
            ui.output_ui("resource_buttons"),
            # View selector buttons and the rest follow below
            ui.tags.div(
                ui.input_action_button("view_output", "Output", class_="button button1",
                                       style="width:90%; margin-bottom:8px;"),
                ui.input_action_button("view_config", "Config", class_="button button1",
                                       style="width:90%; margin-bottom:24px;"),
                style="margin-bottom: 16px;"
            ),
            class_="sidebar",
            id="sidebar"
        ),
        # Main panel
        ui.tags.div(
            ui.output_ui("main_panel"),
            class_="main-panel",
            id="main_panel_wrap"
        ),
        style="display: flex; flex-direction: row;"
    ),
    # Bits of JS to handle sidebar show/hide
    ui.tags.script("""
    document.addEventListener("DOMContentLoaded", function() {
        const sidebar = document.getElementById("sidebar");
        const toggleBtn = document.getElementById("sidebarToggle");
        const mainPanelWrap = document.getElementById("main_panel_wrap");
        toggleBtn.addEventListener("click", function() {
            sidebar.classList.toggle("collapsed");
        });
    });
    """),
    enter_key_js,
    style="box-sizing: border-box; margin: 0; padding: 0;"
)


def run_head_and_capture_output(config_obj, selected_host_value):
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


def server(inputs, outputs, session):
    # Reactive value for output text
    assert session
    terminal_text = reactive.Value("")
    selected_view = reactive.Value("output")  # "output" or "Config"
    selected_resource = reactive.Value(None)
    selected_plc = reactive.Value(None)  # Only when used "all"

    # Add this to store the plc_bits data
    plc_bits_data = reactive.Value([])

    # Add this near the top of your server function where other reactive values are defined
    resource_buttons_trigger = reactive.Value(0)

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

                        # FIX: Use await instead of asyncio.run
                        results = await get_bits()

                        # Store the results in a reactive value
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

                    # FIX: Use await instead of asyncio.run
                    results = await get_bits()

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
        # When "all" is selected, pass "all" directly to run_head_and_capture_output
        # instead of trying to use selected_plc() which could be None
        captured_output = run_head_and_capture_output(config_loader, selected_host_value)
        terminal_text.set(captured_output or "[No output produced]")

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
                ui.tags.h2("PLC Configuration"),  # Title
                # Container for label and text area
                ui.tags.div(
                    ui.tags.label(
                        "Edit PLC Configuration:",
                        **{"for": "yaml_editor"},
                        style="display: block; margin-bottom: 8px; font-size: 1.1rem;"  # Label above the text area
                    ),
                    ui.input_text_area(
                        "yaml_editor",
                        label=None,
                        value=yaml_content,
                        height="600px",  # Larger height
                        width="800px",  # Larger width
                        resize="both"  # Allow resizing in both directions
                    ),
                    style="display: flex; flex-direction: column; align-items: center; margin: 0 auto;"
                    # Center text area
                ),
                # Save button container
                ui.tags.div(
                    ui.input_action_button(
                        "save_config",
                        "Save Changes",
                        class_="button button1",
                        style="margin-top: 16px; padding: 10px 20px;"  # Add margin and padding to the button
                    ),
                    ui.tags.div(
                        ui.output_text("save_status_output"),
                        style="margin-top: 12px; font-weight: bold;"  # Status message styling
                    ),
                    style="display: flex; flex-direction: column; align-items: center; margin-top: 16px;"
                ),
                style="width: 800px; margin: 0 auto; text-align: center;"  # Center the layout with a wider container
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
            return ui.tags.div(
                ui.tags.h2("PLC View"),
                ui.tags.p(f"Geselecteerde PLC: {selected_plc()}"),
                ui.tags.p("PLC content goes here....")
            )
        return None

    @outputs()
    @render.ui
    def resource_buttons():
        # Make this output depend on the trigger
        resource_buttons_trigger()

        selected_hosts = inputs.host_select()
        sftp_hosts = config.get('sftp_hosts', [])

        if not selected_hosts or selected_hosts == "all":
            plc_buttons = []
            for i, host in enumerate(sftp_hosts):
                hostname = host.get('hostname', host.get('ip_address'))
                # Add selects classes if this PLC is currently selected
                class_name = "button button1"
                if selected_plc() == hostname:
                    class_name += " selected"

                plc_buttons.append(
                    ui.input_action_button(f"plc_{i}", hostname,
                                           class_="button button1", style="width:90%; margin-bottom:8px;")
                )

            if not plc_buttons:
                return ui.tags.p("No PLCs found.")
            return ui.tags.div(*plc_buttons)

        host_cfg = next((host for host in sftp_hosts
                         if host.get('hostname') == selected_hosts or host.get('ip_address') == selected_hosts), None)
        if not host_cfg:
            return ui.tags.p("No resources found for this PLC.")

        resources = host_cfg.get('resources', [])
        if not resources:
            return ui.tags.p("No resources found for this PLC.")

        # Highlight which button is active
        buttons = []
        for i, resource in enumerate(resources):
            btn_id = f"resource_{i}"
            class_name = "button button1"
            if selected_resource() == resource:
                class_name += " selected"
            buttons.append(
                ui.input_action_button(btn_id, resource,
                                       class_="button button1", style="width:90%; margin-bottom:8px;")
            )
        return ui.tags.div(*buttons)

    # Inside the server function
    save_message = reactive.Value("")

    # --- Config Save Handler ---
    @reactive.effect
    @reactive.event(inputs.save_config)
    async def save_yaml_config():
        """Handle YAML configuration saving and database synchronization."""
        try:
            # Step 1: Get and validate YAML content
            yaml_content = inputs.yaml_editor()
            test_config = validate_yaml(yaml_content)
            if not test_config:
                return

            # Step 2: Save configuration and update global state
            update_configuration(yaml_content, test_config)

            # Step 3: Update UI components
            update_ui_components()

            # Step 4: Synchronize with database
            await sync_with_database()
        
            # Set success status
            save_message.set("Configuration saved successfully!")

        except Exception as e:
            # Update the reactive value instead of calling set() on an output
            save_message.set(f"Error saving file: {str(e)}")

    def validate_yaml(yaml_content):
        """Validate that the provided content is valid YAML."""
        try:
            test_config = yaml.safe_load(yaml_content)
            return test_config
        except Exception as e:
            save_message.set(f"Error: Invalid YAML format - {str(e)}")
            return None

    def update_configuration(yaml_content, test_config):
        """Save config to file and update global variables."""
        global config, config_loader

        # Save to file
        config_loader.save_config(yaml_content)
        save_message.set("Configuration saved successfully!")

        # Update global config
        config = test_config

        # Reinitialize config loader
        config_loader = ConfigLoader("plc.yaml")

        # Update host options
        global host_options
        host_options = config_loader.get_host_options()

    def update_ui_components():
        """Update UI components to reflect the new configuration."""
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

    async def sync_with_database():
        """Synchronize the configuration with the database."""
        try:
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

    @outputs()
    @render.text
    def save_status_output():
        return save_message()

    # Add this near where other reactive values are defined in the server function
    save_message = reactive.Value("")

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

# Add this reactive value and render function for status messages
    save_message = reactive.Value("")

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