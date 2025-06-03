import yaml

class ConfigLoader:
    """
    Information:
        A class for loading and managing YAML configuration files.
        Provides methods to access specific configuration sections and save updated configurations.

    Parameters:
        Input: Path to a YAML configuration file

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, yaml_path):
        """
        Information:
            Initialize the ConfigLoader with a YAML configuration file path.
            Loads the configuration upon initialization.

        Parameters:
            Input: yaml_path - Path to the YAML configuration file

        Date: 03/06/2025
        Author: TOVY
        """
        self.yaml_path = yaml_path  # Store the path for later use
        with open(yaml_path, "r") as f:
            self.config = yaml.safe_load(f)

    def get_sftp_hosts(self):
        """
        Information:
            Retrieve the SFTP hosts configuration section.

        Parameters:
            Output: List of SFTP host configurations

        Date: 03/06/2025
        Author: TOVY
        """
        return self.config.get("sftp_hosts", [])

    def get_database_info(self):
        """
        Information:
            Retrieve the database configuration section.

        Parameters:
            Output: Dictionary containing database configuration

        Date: 03/06/2025
        Author: TOVY
        """
        return self.config["database"]

    def get_host_options(self):
        """
        Information:
            Returns a dictionary of host options including an 'all' option.
            Maps hostnames or IP addresses to display names.

        Parameters:
            Output: Dictionary with host identifiers as keys and display names as values

        Date: 03/06/2025
        Author: TOVY
        """
        return {
            "all": "All",
            **{
                host.get('hostname', host.get('ip_address')): host.get('hostname', host.get('ip_address'))
                for host in self.get_sftp_hosts()
            }
        }

    def get(self, param, default=None):
        """
        Information:
            Get a parameter from the configuration with validation and error handling.
            Safely retrieves configuration values with a fallback default.

        Parameters:
            Input: param - The parameter name to look up in the configuration
                  default - The default value to return if param is not found
            Output: The value of the parameter or the default value if not found

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            return self.config.get(param, default)
        except (AttributeError, TypeError) as e:
            print(f"Error accessing configuration parameter '{param}': {e}")
            return default

    def save_config(self, yaml_content, yaml_path=None):
        """
        Information:
            Save the provided YAML content to a file.
            Validates the YAML format before saving and updates the internal configuration.
            Uses the original path if no new path is provided.

        Parameters:
            Input: yaml_content - String containing YAML configuration to save
                  yaml_path - Path to save the YAML file to (optional)
            Output: True if successful, raises exception otherwise

        Date: 03/06/2025
        Author: TOVY
        """
        path = yaml_path or self.yaml_path
        # Validate YAML format before saving
        try:
            # Check if it's valid YAML
            test_config = yaml.safe_load(yaml_content)
            
            # Write to file
            with open(path, "w") as file:
                file.write(yaml_content)
                
            # Update the internal config with new content
            self.config = test_config
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {str(e)}")