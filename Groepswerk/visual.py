import sys
import io
import yaml
import os
from shiny import App, ui, render
from shiny import reactive
import head
from shiny import ui

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
            0 8px 32px 4px rgba(0,0,0,0.40),
            0 2px 8px 1px rgba(0,0,0,0.24),
            0 0 0 6px rgba(255,56,1,0.12);
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
            ui.tags.div(
                ui.input_action_button(
                    "start_btn", "Refresh", class_="button button1",
                    style="width:90%; margin-bottom:8px;"
                ),
            ),
            # View selector buttons
            ui.tags.div(
                ui.input_action_button("view_output", "Output", class_="button button1",
                                       style="width:90%; margin-bottom:8px;"),
                ui.input_action_button("view_database", "Database", class_="button button1",
                                       style="width:90%; margin-bottom:24px;"),
                style="margin-bottom: 16px;"
            ),
            # --- Additional sidebar content goes here ---
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
    selected_view = reactive.Value("output")  # "output" or "database"

    # View-switching logic
    @reactive.effect
    @reactive.event(inputs.view_output)
    def _():
        selected_view.set("output")

    @reactive.effect
    @reactive.event(inputs.view_database)
    def _():
        selected_view.set("database")

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
        captured_output = run_head_and_capture_output(config, selected_host_value)
        terminal_text.set(captured_output or "[No output produced]")

    # Main panel UI switching
    @outputs()
    @render.ui
    def main_panel():
        if selected_view() == "output":
            return ui.tags.div(
                ui.output_text("selected_host"),
                ui.tags.h2("Output"),
                ui.output_text_verbatim("terminal_output", placeholder=True)
            )
        elif selected_view() == "database":
            return ui.tags.div(
                ui.tags.h2("Database"),
                ui.tags.p("Database content goes here...")
                # Add any UI elements for your Database view here
            )
        return None


app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app

    run_app(app)
