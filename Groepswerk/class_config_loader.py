import yaml


class ConfigLoader:
    def __init__(self, yaml_path):
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
