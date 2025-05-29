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