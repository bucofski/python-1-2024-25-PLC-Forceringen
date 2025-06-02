from Groepswerk.util.class_config_loader import ConfigLoader
from shiny import App, ui, render, reactive
from Groepswerk.ui.ui_components import (
    create_app_ui, create_resource_buttons_ui, 
    create_resource_table, create_plc_table, create_detail_view, 
    create_config_view, create_output_view
)
from Groepswerk.util.server_functions import (
    run_distributor_and_capture_output, validate_yaml, update_configuration,
    update_ui_components, sync_with_database,
    create_resource_click_handler, create_plc_click_handler,
    create_detail_click_handler, create_save_reason_handler,
    create_back_button_handler, create_save_reason_detail_handler
)
import os

# Read host options from YAML
script_dir = os.path.dirname(os.path.abspath(__file__))
yaml_path = os.path.join(script_dir, "..", "config", "plc.yaml")

try:
    config_loader = ConfigLoader("../config/plc.yaml")
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
    selected_view = reactive.Value("output")  # "output", "Config", "resource", "ALL", or "detail"
    selected_resource = reactive.Value(None)
    selected_plc = reactive.Value(None)  # Only when used "all"
    plc_bits_data = reactive.Value([])
    resource_buttons_trigger = reactive.Value(0)
    save_message = reactive.Value("")
    selected_bit_detail = reactive.Value(None)  # Store selected bit for detail view
    bit_history_data = reactive.Value([])  # Store history data for detail view

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
    @reactive.event(inputs.view_resource)
    def _():
        selected_view.set("resource")

    @reactive.effect
    @reactive.event(inputs.view_all)
    def _():
        selected_view.set("ALL")
        
    @reactive.effect
    @reactive.event(inputs.view_detail)
    def _():
        selected_view.set("detail")

    # Create all event handlers once at startup
    create_resource_click_handler(
        config, inputs, selected_resource, selected_plc, selected_view, plc_bits_data, config_loader
    )
    
    create_plc_click_handler(
        config, inputs, selected_plc, selected_resource, selected_view, plc_bits_data, config_loader
    )
    
    create_detail_click_handler(
        plc_bits_data, inputs, selected_bit_detail, selected_view, bit_history_data, config_loader, selected_plc
    )

    create_save_reason_handler(
        inputs, plc_bits_data, selected_plc, selected_resource, save_message, config_loader
    )

    create_save_reason_detail_handler(
        inputs, selected_bit_detail, selected_plc, selected_resource, save_message, config_loader, bit_history_data
    )
    create_back_button_handler(
        inputs, selected_resource, selected_view, plc_bits_data, config_loader, selected_plc
    )

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
        captured_output = run_distributor_and_capture_output(config_loader, selected_host_value)
        terminal_text.set(captured_output or "[No output produced]")

    @outputs()
    @render.ui
    def resource_buttons():
        # Make this output depend on the trigger
        resource_buttons_trigger()
        return create_resource_buttons_ui(config, inputs, selected_resource, selected_plc)

    @outputs()
    @render.ui
    def main_panel():
        if selected_view() == "output":
            return create_output_view()
        elif selected_view() == "Config":
            return create_config_view(yaml_path)
        elif selected_view() == "resource":
            data = plc_bits_data()
            return create_resource_table(data, selected_resource, selected_plc)
        elif selected_view() == "ALL":
            data = plc_bits_data()
            return create_plc_table(data, selected_plc)
        elif selected_view() == "detail":
            bit_data = selected_bit_detail()
            history_data = bit_history_data()
            return create_detail_view(bit_data, history_data)
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