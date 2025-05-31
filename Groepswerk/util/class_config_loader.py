import yaml


class ConfigLoader:
    def __init__(self, yaml_path):
        self.yaml_path = yaml_path  # Store the path for later use
        with open(yaml_path, "r") as f:
            self.config = yaml.safe_load(f)

    def get_sftp_hosts(self):
        return self.config.get("sftp_hosts", [])

    def get_database_info(self):
        return self.config["database"]

    def get_host_options(self):
        """Returns a dictionary of host options including 'all' option"""
        return {
            "all": "All",
            **{
                host.get('hostname', host.get('ip_address')): host.get('hostname', host.get('ip_address'))
                for host in self.get_sftp_hosts()
            }
        }

    def get(self, param, default=None):
        """
        Get a parameter from the configuration with validation and error handling.

        Args:
            param: The parameter name to look up in the configuration
            default: The default value to return if param is not found (default is None)

        Returns:
            The value of the parameter from the configuration, or the default value
            if the parameter is not found
        """
        try:
            return self.config.get(param, default)
        except (AttributeError, TypeError) as e:
            print(f"Error accessing configuration parameter '{param}': {e}")
            return default

    def save_config(self, yaml_content, yaml_path=None):
        """
        Save the provided YAML content to a file.
        
        Args:
            yaml_content: String containing YAML configuration to save
            yaml_path: Path to save the YAML file to (uses the original path if None)
        
        Returns:
            True if successful, raises exception otherwise
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