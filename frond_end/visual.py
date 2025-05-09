import sys
import io
import yaml
import os
from shiny import App, ui, render
from shiny import reactive
import python-1-2024-25-PLC-Forceringen.Groepswerk.head

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

app_ui = ui.page_fluid(
    ui.input_select(
        "host_select",
        "Select a PLC Host:",
        choices=host_options
    ),
    ui.output_text("selected_host"),
    ui.input_action_button("start_btn", "Start"),
    # Removed 'height' argument from output_text_verbatim
    ui.output_text_verbatim("terminal_output", placeholder=True)
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
