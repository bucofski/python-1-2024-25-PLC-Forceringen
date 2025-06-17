"""
UI Components Module for PLC Management Application

Information:
    This module provides UI components and styling for the Shiny application.
    It includes functions to create resource buttons, application UI layout,
    and CSS styling for a consistent look and feel.

Date: 03/06/2025
Author: TOVY
"""

from shiny import ui

COLOR = "#FB4400"

# Better solution - more specific targeting
enter_key_js = ui.tags.script("""
document.addEventListener('DOMContentLoaded', function() {
    // Single delegated event listener for reason inputs only
    document.addEventListener('keydown', function(event) {
        const target = event.target;
        
        // Only process Enter key on specific reason input fields in data tables/detail view
        if (event.key !== 'Enter' || 
            !target.id || 
            !target.id.startsWith('reason_input_') ||
            target.type !== 'text' ||
            target.closest('.data-grid-container, [style*="max-width: 1000px"]') === null) {
            return;
        }
        
        event.preventDefault();
        
        const forcedInput = document.getElementById(
            target.id.replace('reason_input_', 'forced_input_')
        );
        const forcedValue = forcedInput?.value || '';
        
        // Get melding value for both detail and table views
        const meldingInput = document.getElementById(
            target.id.replace('reason_input_', 'melding_input_')
        );
        const meldingValue = meldingInput?.value || '';
        
        if (target.id === 'reason_input_detail') {
            // Handle detail view
            Shiny.setInputValue('save_reason_detail_triggered', {
                reasonValue: target.value,
                forcedValue: forcedValue,
                meldingValue: meldingValue,
                timestamp: Date.now()
            });
        } else {
            // Handle table view
            const index = target.id.split('_')[2];
            Shiny.setInputValue('save_reason_triggered', {
                index: index,
                reasonValue: target.value,
                forcedValue: forcedValue,
                meldingValue: meldingValue,  // Add this line!
                timestamp: Date.now()
            });
        }
    });
});
""")

# Consolidated CSS styles
TABLE_CSS = """
input[type="text"] {
    width: 100%;
    padding: 6px 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    box-sizing: border-box;
    white-space: nowrap;
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
    white-space: nowrap;
}
.data-grid {
    border-collapse: collapse;
    margin: 0;
}
"""

# Precompiled button styles
BUTTON_STYLES = """
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
    white-space: nowrap;
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

def format_value_display(value, default=''):
    """
    Helper function to format None values as empty strings.
    
    Parameters:
        value: The value to format
        default: Default value if value is None or 'None'
    
    Returns:
        Formatted string value
    """
    return '' if value in (None, 'None') else str(value)

def create_button_with_selection(btn_id, text, is_selected=False, style_override="width:90%; margin-bottom:8px;"):
    """
    Helper function to create buttons with consistent styling and selection state.
    
    Parameters:
        btn_id: Button ID
        text: Button text
        is_selected: Whether button should have selected class
        style_override: Custom style string
    
    Returns:
        UI button element
    """
    class_name = "button button1"
    if is_selected:
        class_name += " selected"
    
    return ui.input_action_button(
        btn_id, text,
        class_="button button1",
        style=style_override
    )

def create_resource_buttons_ui(config, inputs, selected_resource, selected_plc):
    """
    Creates UI buttons for PLC resources based on the current selection.
    Optimized with helper functions and reduced repetition.
    """
    selected_hosts = inputs.host_select()
    sftp_hosts = config.get('sftp_hosts', [])

    if not selected_hosts or selected_hosts == "all":
        if not sftp_hosts:
            return ui.tags.p("No PLCs found.")
        
        plc_buttons = [
            create_button_with_selection(
                f"plc_{i}",
                host.get('hostname', host.get('ip_address')),
                selected_plc() == host.get('hostname', host.get('ip_address'))
            )
            for i, host in enumerate(sftp_hosts)
        ]
        return ui.tags.div(*plc_buttons)

    host_cfg = next((host for host in sftp_hosts
                     if host.get('hostname') == selected_hosts or host.get('ip_address') == selected_hosts), None)
    
    if not host_cfg:
        return ui.tags.p("No resources found for this PLC.")

    resources = host_cfg.get('resources', [])
    if not resources:
        return ui.tags.p("No resources found for this PLC.")

    buttons = [
        create_button_with_selection(
            f"resource_{i}",
            resource,
            selected_resource() == resource
        )
        for i, resource in enumerate(resources)
    ]
    
    return ui.tags.div(*buttons)

def create_table_css():
    """
    Returns optimized CSS styling as a single style tag.
    """
    return ui.tags.style(TABLE_CSS)

def create_table_header(headers):
    """
    Helper function to create table headers.
    
    Parameters:
        headers: List of header strings
    
    Returns:
        Table header row element
    """
    header_cells = [ui.tags.th(header) for header in headers]
    return ui.tags.tr(*header_cells)

def create_table_row(item, index, include_reason_inputs=True, include_resource=False):
    """
    Helper function to create table rows with consistent formatting.
    
    Parameters:
        item: Data item dictionary
        index: Row index
        include_reason_inputs: Whether to include reason/forced_by inputs
        include_resource: Whether to include resource column
    
    Returns:
        Table row element
    """
    # Format datetime
    forced_at = item.get('forced_at')
    forced_at_str = forced_at.strftime("%d-%m-%Y") if forced_at else ""
    
    # Format values
    comment = format_value_display(item.get('comment', ''))
    second_comment = format_value_display(item.get('second_comment', ''))
    forced_by = format_value_display(item.get('forced_by', ''))
    melding = format_value_display(item.get('melding', ''))
    reason = format_value_display(item.get('reason', ''))
    
    # Create row class
    row_class = "force-active" if item.get('force_active') else ""
    
    # Base cells
    cells = []
    
    # Add resource column if needed
    if include_resource:
        cells.append(ui.tags.td(item.get('resource', '')))
    
    # Common cells
    cells.extend([
        ui.tags.td(item.get('bit_number', '')),
        ui.tags.td(item.get('kks', '')),
        ui.tags.td(comment),
        ui.tags.td(second_comment),
        ui.tags.td(item.get('value', '')),
        ui.tags.td(forced_at_str),
    ])
    
    # Add input fields if needed
    if include_reason_inputs:
        cells.extend([
            ui.tags.td(ui.input_text(f"forced_input_{index}", "", value=forced_by, placeholder="Enter user...")),
            ui.tags.td(ui.input_text(f"melding_input_{index}", "", value=melding, placeholder="Enter user...")),
            ui.tags.td(ui.input_text(f"reason_input_{index}", "", value=reason, placeholder="Enter reason...")),
        ])
    else:
        cells.append(ui.tags.td(forced_by))
    
    # Add detail button
    cells.append(
        ui.tags.td(ui.input_action_button(
            f"detail_btn_{index}",
            "View Details",
            class_="btn btn-primary btn-sm",
            style="padding: 4px 8px; font-size: 12px;"
        ))
    )
    
    return ui.tags.tr(*cells, class_=row_class, id=f"bit_row_{index}")

def create_resource_table(data, selected_resource, selected_plc):
    """
    Creates a table to display bit data for a specific resource.
    Optimized with helper functions.
    """
    if not data:
        return ui.tags.div(
            ui.tags.h2(f"Resource: {selected_resource()}"),
            ui.tags.p("No data available for this resource.")
        )

    headers = [
        "Sign. Name", "KKS", "Comment", "Second Comment", "Value",
        "Forced at", "Forced by","Ticket nr.", "Reason", "Details"
    ]

    header_row = create_table_header(headers)
    rows = [create_table_row(item, i) for i, item in enumerate(data)]

    table = ui.tags.table(
        ui.tags.thead(header_row),
        ui.tags.tbody(*rows),
        class_="data-grid"
    )

    return ui.tags.div(
        ui.tags.h2(f"Resource: {selected_resource()} on PLC: {selected_plc()}"),
        create_table_css(),
        ui.tags.div(table, class_="data-grid-container"),
        ui.output_text("save_status")
    )

def create_plc_table(data, selected_plc):
    """
    Creates a table to display all bit data for a specific PLC across all resources.
    Optimized with helper functions.
    """
    if not data:
        return ui.tags.div(
            ui.tags.h2(f"PLC: {selected_plc()}"),
            ui.tags.p("No data available for this PLC.")
        )

    headers = [
        "Resource", "Sign. Name", "KKS", "Comment", "Second Comment", "Value",
        "Forced at", "Forced by", "Details"
    ]

    header_row = create_table_header(headers)
    rows = [create_table_row(item, i, include_reason_inputs=False, include_resource=True) 
            for i, item in enumerate(data)]

    table = ui.tags.table(
        ui.tags.thead(header_row),
        ui.tags.tbody(*rows),
        class_="data-grid"
    )

    return ui.tags.div(
        ui.tags.h2(f"PLC: {selected_plc()}"),
        create_table_css(),
        ui.tags.div(table, class_="data-grid-container"),
        ui.output_text("save_status")
    )

def create_info_card(title, content_dict, style_class="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;"):
    """
    Helper function to create information cards.
    
    Parameters:
        title: Card title
        content_dict: Dictionary of label-value pairs
        style_class: CSS style string
    
    Returns:
        Styled div element
    """
    content_items = [
        ui.tags.div(
            ui.tags.strong(f"{label}: "), str(value),
            style="margin-bottom: 10px;"
        )
        for label, value in content_dict.items()
    ]
    
    return ui.tags.div(
        ui.tags.h3(title),
        ui.tags.div(*content_items, style=style_class)
    )

def create_detail_view(bit_data, history_data):
    """
    Creates a detailed view for a specific bit.
    Optimized with helper functions and reduced repetition.
    """
    if not bit_data:
        return ui.tags.div(
            ui.tags.h2("Detail View"),
            ui.tags.p("No bit selected for detail view.")
        )

    # Format datetime
    forced_at = bit_data.get('forced_at')
    forced_at_str = forced_at.strftime("%d-%m-%Y %H:%M:%S") if forced_at else "Not forced"

    # Format input values - FIX: Get both reason and melding separately
    forced_by = format_value_display(bit_data.get('forced_by', ''))
    reason = format_value_display(bit_data.get('reason', ''))
    melding = format_value_display(bit_data.get('melding', ''))  # Add this line

    back_button = ui.input_action_button(
        "back_to_list", "← Back to List",
        class_="btn btn-secondary",
        style="margin-bottom: 20px;"
    )

    # Create information cards
    bit_info_card = create_info_card("Bit Information", {
        "Signal name": bit_data.get('bit_number', 'N/A'),
        "KKS": bit_data.get('kks', 'N/A'),
        "Resource": bit_data.get('resource', 'N/A'),
        "Value": str(bit_data.get('value', 'N/A')),
        "Variable type": str(bit_data.get('var_type', 'N/A')),
        "Force Active": "Yes" if bit_data.get('force_active') else "No"
    })

    comments_card = create_info_card("Comments", {
        "Comment": bit_data.get('comment', 'None') if bit_data.get('comment') != 'None' else 'No comment',
        "Second Comment": bit_data.get('second_comment', 'None') if bit_data.get('second_comment') != 'None' else 'No comment'
    })

    # Force information with input fields
    force_info = ui.tags.div(
        ui.tags.h3("Current Force Information"),
        ui.tags.div(
            ui.tags.div(ui.tags.strong("Forced at: "), forced_at_str, style="margin-bottom: 10px;"),
            ui.tags.div(
                ui.tags.strong("Forced by: "),
                ui.input_text("forced_input_detail", "", value=forced_by, placeholder="Enter user..."),
                style="margin-bottom: 10px;"
            ),
            ui.tags.div(
                ui.tags.strong("Ticket nr.: "),
                ui.input_text("melding_input_detail", "", value=melding, placeholder="Enter ticket..."),  # FIX: Use 'melding' here
                style="margin-bottom: 10px;"
            ),
            ui.tags.div(
                ui.tags.strong("Reason: "),
                ui.input_text("reason_input_detail", "", value=reason, placeholder="Enter reason..."),  # Keep 'reason' here
                style="margin-bottom: 10px;"
            ),
            style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;"
        )
    )

    # Create history section
    if history_data:
        history_headers = ["Forced at", "Deforced at", "Value", "Ticket nr.", "Forced by", "Reason"]
        history_header_row = create_table_header(history_headers)
        
        history_rows = []
        for hist_item in history_data:
            forced_at_hist = hist_item.get('forced_at')
            forced_at_str_hist = forced_at_hist.strftime("%d-%m-%Y %H:%M:%S") if forced_at_hist else "N/A"
            
            deforced_at_hist = hist_item.get('deforced_at')
            deforced_at_str_hist = (
                deforced_at_hist.strftime("%d-%m-%Y %H:%M:%S") if deforced_at_hist 
                else ("Still Active" if hist_item == history_data[0] else "N/A")
            )
            valued_hist = hist_item.get('value')
            order_hist = hist_item.get('melding')
            forced_by_hist = format_value_display(hist_item.get('forced_by', 'Unknown'), 'Unknown')
            reason_hist = format_value_display(hist_item.get('reason', 'No reason'), 'No reason')
            
            hist_cells = [
                ui.tags.td(forced_at_str_hist),
                ui.tags.td(deforced_at_str_hist),
                ui.tags.td(valued_hist),
                ui.tags.td(order_hist),
                ui.tags.td(forced_by_hist),
                ui.tags.td(reason_hist)
            ]
            
            history_rows.append(ui.tags.tr(*hist_cells))

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
        bit_info_card,
        comments_card,
        force_info,
        history_section,
        ui.output_text("save_status"),
        style="max-width: 1000px; margin: 0 auto;"
    )

def create_config_view(yaml_path):
    """
    Creates the configuration editing view.
    Optimized file reading with context manager.
    """
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
                rows=50,
                cols=100,
                width="100%",
                resize="both"
            ),
            style="display: flex; flex-direction: column; align-items: center; margin: 0 auto; width: 100%;"
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
        style="width: 600px; margin: 0 auto; text-align: center;"
    )

def create_output_view():
    """
    Creates the output view for displaying terminal output.
    """
    return ui.tags.div(
        ui.output_text("selected_host"),
        ui.tags.h2("Output"),
        ui.output_text_verbatim("terminal_output", placeholder=True)
    )

def create_app_ui(host_options):
    """
    Creates the main application UI with all components.
    Optimized CSS consolidation and reduced inline styles.
    """
    # Consolidated font and main styles
    MAIN_STYLES = f"""
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
        padding: 20px;
        color: white;
        height: calc(100vh - 70px);
        width: 220px;
        box-sizing: border-box;
        position: fixed;
        top: 70px;
        left: 0;
        transition: transform 0.2s cubic-bezier(.42,0,.58,1);
        text-align: center;
        z-index: 110;
        overflow-y: auto;
    }}
    .sidebar.collapsed {{
        transform: translateX(-220px);
    }}
    .sidebar-content {{
        display: flex;
        flex-direction: column;
        min-height: 100%;
    }}
    .sidebar-top {{
        flex: 1;
    }}
    .sidebar-bottom {{
        margin-top: 20px;
        padding-top: 10px;
        border-top: 1px solid rgba(255,255,255,0.2);
        padding-bottom: 20px;
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
        left: 10px;
        top: 20px;
        z-index: 120;
        background-color: {COLOR};
        color: white;
        border: none;
        border-radius: 50%;
        width: 36px;
        height: 36px;
        cursor: pointer;
        font-size: 18px;
        outline: none;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow:
        0 4px 12px 2px rgba(0,0,0,0.18),
        0 1px 4px 0 rgba(0,0,0,0.10),
        0 0 0 3px rgba(255,56,1,0.10);
        transition: box-shadow 0.3s;
    }}
    #host_select-label, select#host_select {{
        font-size: 1.25rem;
        padding: 10px;
        height: 48px;
        width: 90%;
        font-family: 'VAGRoundedLight';
    }}
    h1 {{
        text-shadow:
            0 4px 24px rgba(0,0,0,0.45),
            0 1.5px 0 rgba(0,0,0,0.28),
            0 0 12px {COLOR}55;
    }}
    """

    # Consolidated sidebar toggle JavaScript
    SIDEBAR_JS = """
    document.addEventListener("DOMContentLoaded", function() {
        const sidebar = document.getElementById("sidebar");
        const toggleBtn = document.getElementById("sidebarToggle");
        
        toggleBtn.addEventListener("click", function() {
            sidebar.classList.toggle("collapsed");
        });
    });
    """

    return ui.tags.div(
        # All CSS in one place
        ui.tags.style(MAIN_STYLES),
        ui.tags.style(BUTTON_STYLES),
        
        # Top bar
        ui.tags.div(
            ui.tags.h1(
                "PLC Overrides",
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
        
        # Page layout
        ui.tags.div(
            # Sidebar
            ui.tags.div(
                ui.tags.div(
                    ui.tags.div(
                        ui.tags.div(
                            ui.input_select("host_select", "Select PLC:", choices=host_options),
                            style="margin-bottom: 8px;"
                        ),
                        ui.tags.div(
                            ui.input_action_button(
                                "start_btn", "Get Overrides", class_="button button1",
                                style="width:90%; margin-bottom:20px;"
                            ),
                            "Show Overrides:",
                        ),
                        ui.output_ui("resource_buttons"),
                        class_="sidebar-top"
                    ),
                    ui.tags.div(
                        ui.input_action_button("view_output", "Output", class_="button button1",
                                               style="width:90%; margin-bottom:8px;"),
                        ui.input_action_button("view_config", "Config", class_="button button1",
                                               style="width:90%; margin-bottom:8px;"),
                        class_="sidebar-bottom"
                    ),
                    class_="sidebar-content"
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
        
        # JavaScript
        ui.tags.script(SIDEBAR_JS),
        enter_key_js,
        style="box-sizing: border-box; margin: 0; padding: 0;"
    )