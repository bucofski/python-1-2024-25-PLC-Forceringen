import sys
import io
import yaml
import os
from shiny import App, ui, render
from shiny import reactive
import head

# Read host options from YAML
script_dir = os.path.dirname(os.path.abspath(__file__))
yaml_path = os.path.join(script_dir, "..", "Groepswerk", "plc.yaml")

try:
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    raise RuntimeError(
        f"YAML config file not found: {yaml_path}\n"
        "Please make sure 'plc.yaml' exists in the Groepswerk folder next to this script."
    )

host_options = {
    "all": "All",  # Add this line
    **{
        host.get('hostname', host.get('ip_address')): host.get('hostname', host.get('ip_address'))
        for host in config.get('sftp_hosts', [])
    }
}

COLOR = "#FB4400"

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
            # Refresh button stays at the very top (right after host select)
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
    # Bit of JS to handle sidebar show/hide
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
    style="box-sizing: border-box; margin: 0; padding: 0;"
)


def run_head_and_capture_output(config_output, selected_host_value):
    buffer = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = sys.stderr = buffer
    try:
        if selected_host_value == "all":
            # For 'all', call it for every host in the yaml
            for host in config_output.get('sftp_hosts', []):
                host_name = host.get('hostname', host.get('ip_address'))
                print(f"=== {host_name} ===")
                head.run_main_with_host(config_output, host_name)
                print()
        else:
            head.run_main_with_host(config_output, selected_host_value)
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
    def handle_resource_clicks():
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
                        # Find which PLC this resource belongs to
                        host_name = host.get("hostname", host.get("ip_address"))
                        # Set the resource selection
                        selected_resource.set(resource)
                        # Update the PLC selection to maintain parent-child relationship
                        selected_plc.set(host_name)
                        selected_view.set("resource")
                        print(f"Selected resource: {resource} on PLC: {host_name}")
                        print(f"Selected view: {selected_view()}")

    @reactive.effect
    def handle_plc_clicks():
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
                    # Set PLC selection
                    selected_plc.set(hostname)
                    # IMPORTANT: Clear resource selection when PLC changes
                    selected_resource.set(None)
                    selected_view.set("ALL")

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
        captured_output = run_head_and_capture_output(config, selected_host_value)
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
            return ui.tags.div(
                ui.tags.h2("Resource"),
                ui.tags.p(f"Geselecteerde resource: {selected_resource()}"),
                ui.tags.p("Resource content goes here...")
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

    # Inside the server function
    save_status = reactive.Value("")

    @reactive.effect
    @reactive.event(inputs.save_config)
    def save_yaml_config():
        try:
            # Get the content from the text area
            yaml_content = inputs.yaml_editor()

            # Validate YAML format before saving
            try:
                # Check if it's valid YAML
                test_config = yaml.safe_load(yaml_content)

                # Write to file
                with open(yaml_path, "w") as file:
                    file.write(yaml_content)

                # Update save status
                save_status.set("Configuration saved successfully!")

                # Update the config variable with new content
                global config, host_options
                config = test_config

                # Update host options based on the new config
                host_options = {
                    "all": "All",
                    **{
                        host.get('hostname', host.get('ip_address')): host.get('hostname', host.get('ip_address'))
                        for host in config.get('sftp_hosts', [])
                    }
                }

                # Update the input select component with new options
                ui.update_select(
                    "host_select",
                    choices=host_options
                )

            except yaml.YAMLError as e:
                save_status.set(f"Error: Invalid YAML format - {str(e)}")

        except Exception as e:
            save_status.set(f"Error saving file: {str(e)}")

    @outputs()
    @render.text
    def save_status_output():
        return save_status.get()


app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app

    run_app(app)
