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
    host.get('hostname', host.get('ip_address')): host.get('hostname', host.get('ip_address'))
    for host in config.get('sftp_hosts', [])
}

COLOR = "#FF3801"

app_ui = ui.tags.div(
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
        }
        .button1 {
          background-color: white;
          color: black;
          border: 2px solid #04AA6D;
        }
        .button1:hover {
          background-color: #04AA6D;
          color: white;
        }
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
            padding: 0;
            margin: 0;
            box-sizing: border-box;
            position: fixed;
            top: 0;
            left: 0;
            height: 70px;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 100;
        """
    ),
    # Page layout: sidebar + main area
    ui.tags.div(
        ui.tags.div(
            # Selection box with extra space
            ui.tags.div(
                ui.input_select(
                    "host_select",
                    ui.tags.div("Select a PLC Host:", style="margin-bottom: 18px;"),
                    choices=host_options,
                ),
                style="margin-bottom: 32px;"
            ),
            # Replace Start button with styled HTML button classes
            ui.tags.div(
                ui.input_action_button(
                    "start_btn", "Start",
                    class_="button button1"  # <-- Custom CSS classes
                ),
            ),
            style=(
                f"background: {COLOR};"
                "padding: 20px; color: white; min-height: 100vh; "
                "width: 220px; box-sizing: border-box; position: fixed; top: 70px; left: 0;"
                "text-align: center;"
            )
        ),
        ui.tags.div(
            ui.output_text("selected_host"),
            ui.tags.h2("Output"),
            ui.output_text_verbatim("terminal_output", placeholder=True),
            style="margin-left: 240px; padding: 90px 30px 30px 30px;"
        ),
        style="display: flex; flex-direction: row;"
    ),
    style="box-sizing: border-box; margin: 0; padding: 0;"
)


def run_head_and_capture_output(config, selected_host_value):
    # Capture both stdout and stderr
    buffer = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = sys.stderr = buffer
    try:
        head.run_main_with_host(config, selected_host_value)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Restore sys.stdout and sys.stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return buffer.getvalue()


def server(input, output, session):
    # Reactive value for output text
    terminal_text = reactive.Value("")

    @output()
    @render.text
    def selected_host():
        return f"Selected Host: {input.host_select()}"

    @output()
    @render.text
    def terminal_output():
        return terminal_text()

    @reactive.effect
    @reactive.event(input.start_btn)
    def on_start():
        selected_host_value = input.host_select()
        captured_output = run_head_and_capture_output(config, selected_host_value)
        terminal_text.set(captured_output or "[No output produced]")


app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app

    run_app(app)
