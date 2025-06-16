import yaml
import sys
import io
from shiny import ui
from Forceringen.util import distributor


def run_distributor_and_capture_output(config_obj, selected_host_value):
    """
    Information:
        Captures output from head module execution by temporarily redirecting
        stdout and stderr to a buffer. Handles execution for a single host or
        all hosts based on the selected value.

    Parameters:
        Input: config_obj - ConfigLoader instance with application configuration
              selected_host_value - String specifying the host to process or "all"
        Output: String containing the captured console output

    Date: 03/06/2025
    Author: TOVY
    """
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
                distributor.run_main_with_host(config_obj, host_name, is_gui_context=True)
                print()
        else:
            distributor.run_main_with_host(config_obj, selected_host_value, is_gui_context=True)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return buffer.getvalue()


def validate_yaml(yaml_content, save_message):
    """
    Information:
        Validates that the provided content is valid YAML by attempting to parse it.
        Updates the save_message if validation fails.

    Parameters:
        Input: yaml_content - String containing YAML content to validate
              save_message - Reactive value to update with error messages
        Output: Parsed YAML content as Python object or None if validation fails

    Date: 03/06/2025
    Author: TOVY
    """
    try:
        test_config = yaml.safe_load(yaml_content)
        return test_config
    except Exception as e:
        save_message.set(f"Error: Invalid YAML format - {str(e)}")
        return None


def update_configuration(yaml_content, test_config, config_loader, save_message):
    """
    Information:
        Saves the configuration to file and updates the application's configuration objects.
        Updates the save_message with success status.

    Parameters:
        Input: yaml_content - String containing valid YAML content
              test_config - Parsed YAML configuration
              config_loader - Current ConfigLoader instance
              save_message - Reactive value to update with status messages
        Output: Tuple containing (updated config object, new ConfigLoader instance)

    Date: 03/06/2025
    Author: TOVY
    """
    # Save to file
    config_loader.save_config(yaml_content)
    save_message.set("Configuration saved successfully!")

    # Reinitialize config loader
    config_loader = ConfigLoader(yaml_path=config_loader.yaml_path)

    return test_config, config_loader


def update_ui_components(config_loader, inputs, selected_resource, resource_buttons_trigger):
    """
    Information:
        Updates UI components to reflect the new configuration.
        This includes updating the host select dropdown and handling
        resource selection if a previously selected resource no longer exists.

    Parameters:
        Input: config_loader - Updated ConfigLoader instance
              inputs - Shiny inputs object
              selected_resource - Reactive value for the selected resource
              resource_buttons_trigger - Reactive value to trigger resource buttons refresh

    Date: 03/06/2025
    Author: TOVY
    """
    host_options = config_loader.get_host_options()

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