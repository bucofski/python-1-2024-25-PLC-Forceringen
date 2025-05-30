from shiny import ui

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

def create_resource_buttons_ui(config, inputs, selected_resource, selected_plc):
    """Create resource buttons UI based on current selection"""
    selected_hosts = inputs.host_select()
    sftp_hosts = config.get('sftp_hosts', [])

    if not selected_hosts or selected_hosts == "all":
        plc_buttons = []
        for i, host in enumerate(sftp_hosts):
            hostname = host.get('hostname', host.get('ip_address'))
            # Add selected class if this PLC is currently selected
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

def create_table_css():
    """Create CSS for input fields and tables"""
    return ui.tags.style("""
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
        .btn-sm {
            padding: 4px 8px;
            font-size: 12px;
            border-radius: 3px;
        }
        .data-grid th {
            background-color: #e9ecef;
            padding: 8px;
            text-align: left;
            border: 1px solid #dee2e6;
            font-weight: bold;
        }
        .data-grid td {
            padding: 8px;
            border: 1px solid #dee2e6;
            vertical-align: top;
        }
        .data-grid {
            border-collapse: collapse;
            margin: 0;
        }
    """)

def create_resource_table(data, selected_resource, selected_plc):
    """Create table for resource view"""
    if not data:
        return ui.tags.div(
            ui.tags.h2(f"Resource: {selected_resource()}"),
            ui.tags.p("No data available for this resource.")
        )

    # Create column headers - added "Details" column
    headers = [
        "Bit Number", "KKS",
        "Comment", "Second Comment", "Value",
        "Forced At", "forced by", "Reason", "Details"
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
        detail_btn_id = f"detail_btn_{i}"

        cells = [
            ui.tags.td(item.get('bit_number', '')),
            ui.tags.td(item.get('kks', '')),
            ui.tags.td(comment),
            ui.tags.td(second_comment),
            ui.tags.td(item.get('value', '')),
            ui.tags.td(forced_at_str),
            ui.tags.td(ui.input_text(forced_id, "", value=forced_by, placeholder="Enter user...")),
            ui.tags.td(ui.input_text(reason_id, "", value=reason, placeholder="Enter reason...")),
            ui.tags.td(ui.input_action_button(
                detail_btn_id,
                "View Details",
                class_="btn btn-primary btn-sm",
                style="padding: 4px 8px; font-size: 12px;"
            ))
        ]

        rows.append(ui.tags.tr(*cells, class_=row_class, id=f"bit_row_{i}"))

    # Build the complete table
    table = ui.tags.table(
        ui.tags.thead(header_row),
        ui.tags.tbody(*rows),
        class_="data-grid"
    )

    # Return the final UI component
    return ui.tags.div(
        ui.tags.h2(f"Resource: {selected_resource()} on PLC: {selected_plc()}"),
        create_table_css(),
        ui.tags.div(
            table,
            class_="data-grid-container"
        ),
        ui.output_text("save_status")
    )

def create_plc_table(data, selected_plc):
    """Create table for PLC view (all resources)"""
    if not data:
        return ui.tags.div(
            ui.tags.h2(f"PLC: {selected_plc()}"),
            ui.tags.p("No data available for this PLC.")
        )

    # Create column headers - added "Details" column
    headers = [
        "resource", "Bit Number", "KKS",
        "Comment", "Second Comment", "Value",
        "Forced At", "forced by", "Details"
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
        detail_btn_id = f"detail_btn_{i}"

        cells = [
            ui.tags.td(item.get('resource', '')),
            ui.tags.td(item.get('bit_number', '')),
            ui.tags.td(item.get('kks', '')),
            ui.tags.td(comment),
            ui.tags.td(second_comment),
            ui.tags.td(item.get('value', '')),
            ui.tags.td(forced_at_str),
            ui.tags.td(item.get('forced_by', '')),
            ui.tags.td(ui.input_action_button(
                detail_btn_id,
                "View Details",
                class_="btn btn-primary btn-sm",
                style="padding: 4px 8px; font-size: 12px;"
            ))
        ]

        rows.append(ui.tags.tr(*cells, class_=row_class, id=f"bit_row_{i}"))

    # Build the complete table
    table = ui.tags.table(
        ui.tags.thead(header_row),
        ui.tags.tbody(*rows),
        class_="data-grid"
    )

    # Return the final UI component
    return ui.tags.div(
        ui.tags.h2(f"PLC: {selected_plc()}"),
        create_table_css(),
        ui.tags.div(
            table,
            class_="data-grid-container"
        ),
        ui.output_text("save_status")
    )

def create_detail_view(bit_data, history_data):
    """Create detailed view for a specific bit"""
    if not bit_data:
        return ui.tags.div(
            ui.tags.h2("Detail View"),
            ui.tags.p("No bit selected for detail view.")
        )

    # Format datetime for display
    forced_at = bit_data.get('forced_at')
    if forced_at:
        forced_at_str = forced_at.strftime("%d-%m-%Y %H:%M:%S")
    else:
        forced_at_str = "Not forced"

    # Create a back button to return to previous view
    back_button = ui.input_action_button(
        "back_to_list",
        "← Back to List",
        class_="btn btn-secondary",
        style="margin-bottom: 20px;"
    )

    # Create detail information cards
    detail_info = ui.tags.div(
        ui.tags.div(
            ui.tags.h3("Bit Information"),
            ui.tags.div(
                ui.tags.div(
                    ui.tags.strong("Bit Number: "), bit_data.get('bit_number', 'N/A'),
                    style="margin-bottom: 10px;"
                ),
                ui.tags.div(
                    ui.tags.strong("KKS: "), bit_data.get('kks', 'N/A'),
                    style="margin-bottom: 10px;"
                ),
                ui.tags.div(
                    ui.tags.strong("Resource: "), bit_data.get('resource', 'N/A'),
                    style="margin-bottom: 10px;"
                ),
                ui.tags.div(
                    ui.tags.strong("Value: "), str(bit_data.get('value', 'N/A')),
                    style="margin-bottom: 10px;"
                ),
                ui.tags.div(
                    ui.tags.strong("Force Active: "),
                    "Yes" if bit_data.get('force_active') else "No",
                    style="margin-bottom: 10px;"
                ),
                style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;"
            )
        ),
        ui.tags.div(
            ui.tags.h3("Comments"),
            ui.tags.div(
                ui.tags.div(
                    ui.tags.strong("Comment: "),
                    bit_data.get('comment', 'None') if bit_data.get('comment') != 'None' else 'No comment',
                    style="margin-bottom: 10px;"
                ),
                ui.tags.div(
                    ui.tags.strong("Second Comment: "),
                    bit_data.get('second_comment', 'None') if bit_data.get('second_comment') != 'None' else 'No comment',
                    style="margin-bottom: 10px;"
                ),
                style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;"
            )
        ),
        ui.tags.div(
            ui.tags.h3("Current Force Information"),
            ui.tags.div(
                ui.tags.div(
                    ui.tags.strong("Forced At: "), forced_at_str,
                    style="margin-bottom: 10px;"
                ),
                ui.tags.div(
                    ui.tags.strong("Forced By: "),
                    bit_data.get('forced_by', 'None') if bit_data.get('forced_by') != 'None' else 'Not specified',
                    style="margin-bottom: 10px;"
                ),
                ui.tags.div(
                    ui.tags.strong("Reason: "),
                    bit_data.get('reason', 'None') if bit_data.get('reason') != 'None' else 'No reason provided',
                    style="margin-bottom: 10px;"
                ),
                style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;"
            )
        )
    )

    # Create history section
    if history_data:
        # Create history table headers
        history_headers = ["Forced At", "Deforced At", "Forced By", "Reason"]
        history_header_cells = [ui.tags.th(header) for header in history_headers]
        history_header_row = ui.tags.tr(*history_header_cells)

        # Create history table rows
        history_rows = []
        for hist_item in history_data:
            # Format dates
            forced_at_hist = hist_item.get('forced_at')
            if forced_at_hist:
                forced_at_str_hist = forced_at_hist.strftime("%d-%m-%Y %H:%M:%S")
            else:
                forced_at_str_hist = "N/A"

            deforced_at_hist = hist_item.get('deforced_at')
            if deforced_at_hist:
                deforced_at_str_hist = deforced_at_hist.strftime("%d-%m-%Y %H:%M:%S")
            else:
                deforced_at_str_hist = "Still Active" if hist_item == history_data[0] else "N/A"

            # Format None values
            forced_by_hist = hist_item.get('forced_by', 'Unknown')
            if forced_by_hist == 'None':
                forced_by_hist = 'Unknown'

            reason_hist = hist_item.get('reason', 'No reason')
            if reason_hist == 'None':
                reason_hist = 'No reason'

            hist_cells = [
                ui.tags.td(forced_at_str_hist),
                ui.tags.td(deforced_at_str_hist),
                ui.tags.td(forced_by_hist),
                ui.tags.td(reason_hist)
            ]

            history_rows.append(ui.tags.tr(*hist_cells))

        # Build the history table
        history_table = ui.tags.table(
            ui.tags.thead(history_header_row),
            ui.tags.tbody(*history_rows),
            class_="data-grid",
            style="width: 100%; font-size: 14px;"
        )

        history_section = ui.tags.div(
            ui.tags.h3("Force History (Last 5 Records)"),
            ui.tags.div(
                history_table,
                style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto;"
            )
        )
    else:
        history_section = ui.tags.div(
            ui.tags.h3("Force History"),
            ui.tags.div(
                ui.tags.p("No force history available for this bit."),
                style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;"
            )
        )

    return ui.tags.div(
        back_button,
        create_table_css(),
        ui.tags.h2(f"Detail View - Bit {bit_data.get('bit_number', 'N/A')}"),
        detail_info,
        history_section,
        style="max-width: 1000px; margin: 0 auto;"
    )

def create_config_view(yaml_path):
    """Create configuration editing view"""
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

def create_output_view():
    """Create output view for terminal display"""
    return ui.tags.div(
        ui.output_text("selected_host"),
        ui.tags.h2("Output"),
        ui.output_text_verbatim("terminal_output", placeholder=True)
    )

def create_app_ui(host_options):
    """Create the main application UI"""
    return ui.tags.div(
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