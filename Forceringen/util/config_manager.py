import yaml
import os

class ConfigLoader:
    """
    Information:
        A class for loading and managing multiple YAML configuration files.
        Provides methods to access specific configuration sections and save updated configurations.
        Loads both plc.yaml and config.yaml files and merges their configurations.

    Parameters:
        Input: Path to the primary YAML configuration file (plc.yaml)

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, yaml_path):
        """
        Information:
            Initialize the ConfigLoader with a YAML configuration file path.
            Loads both plc.yaml and config.yaml configurations upon initialization.

        Parameters:
            Input: yaml_path - Path to the primary YAML configuration file (plc.yaml)

        Date: 03/06/2025
        Author: TOVY
        """
        self.yaml_path = yaml_path  # Store the primary path for later use
        
        # Load primary config (plc.yaml)
        with open(yaml_path, "r") as f:
            self.config = yaml.safe_load(f) or {}
        
        # Determine config.yaml path (same directory as plc.yaml)
        config_dir = os.path.dirname(yaml_path)
        self.config_yaml_path = os.path.join(config_dir, "config.yaml")
        
        # Load secondary config (config.yaml) if it exists
        self.secondary_config = {}
        if os.path.exists(self.config_yaml_path):
            try:
                with open(self.config_yaml_path, "r") as f:
                    self.secondary_config = yaml.safe_load(f) or {}
                print(f"Loaded secondary config from: {self.config_yaml_path}")
            except Exception as e:
                print(f"Warning: Could not load config.yaml: {e}")
                self.secondary_config = {}
        else:
            print(f"Warning: config.yaml not found at {self.config_yaml_path}")

    def get_sftp_hosts(self):
        """
        Information:
            Retrieve the SFTP hosts configuration section from plc.yaml.
            Merges each host with default credentials from config.yaml.

        Parameters:
            Output: List of SFTP host configurations with merged default credentials

        Date: 03/06/2025
        Author: TOVY
        """
        hosts = self.config.get("sftp_hosts", [])
        default_credentials = self.get_credentials()
        
        # Merge default credentials with each host
        enhanced_hosts = []
        for host in hosts:
            enhanced_host = host.copy()
            
            # Add default credentials if not present in host config
            if 'username' not in enhanced_host and 'username' in default_credentials:
                enhanced_host['username'] = default_credentials['username']
            if 'password' not in enhanced_host and 'password' in default_credentials:
                enhanced_host['password'] = default_credentials['password']
            if 'port' not in enhanced_host and 'port' in default_credentials:
                enhanced_host['port'] = default_credentials['port']
                
            enhanced_hosts.append(enhanced_host)
        
        return enhanced_hosts

    def get_database_info(self):
        """
        Information:
            Retrieve the database configuration section.
            First tries to get it from config.yaml, then falls back to plc.yaml.
            Ensures all required fields have default values.

        Parameters:
            Output: Dictionary containing database configuration

        Date: 03/06/2025
        Author: TOVY
        """
        db_config = {}
        
        # Try to get database config from secondary config first (config.yaml)
        if "database" in self.secondary_config:
            db_config = self.secondary_config["database"].copy()
        # Fall back to primary config (plc.yaml)
        elif "database" in self.config:
            db_config = self.config["database"].copy()
        else:
            # If neither has database config, raise an error
            raise KeyError("Database configuration not found in either config.yaml or plc.yaml")
        
        # Ensure all required fields have default values
        defaults = {
            "host": "localhost",
            "port": 1433,
            "database": None,
            "trusted_connection": True,
            "driver": "ODBC Driver 17 for SQL Server"
        }
        
        for key, default_value in defaults.items():
            if key not in db_config or db_config[key] is None:
                db_config[key] = default_value
        
        return db_config

    def get_credentials(self):
        """
        Information:
            Retrieve username/password credentials from config.yaml.
            These are typically used for non-database authentication (like SFTP).

        Parameters:
            Output: Dictionary containing username, password, and port if available

        Date: 03/06/2025
        Author: TOVY
        """
        credentials = {}
        if self.secondary_config:
            credentials["username"] = self.secondary_config.get("username")
            credentials["password"] = self.secondary_config.get("password")
            # This port is for SFTP, not database
            credentials["port"] = self.secondary_config.get("port", 22000)
        return credentials

    def get_sftp_config(self):
        """
        Information:
            Get SFTP-specific configuration including default credentials.
            Merges host-specific config with global SFTP credentials.

        Parameters:
            Output: Dictionary containing SFTP configuration

        Date: 03/06/2025
        Author: TOVY
        """
        sftp_config = {
            "hosts": self.get_sftp_hosts(),
            "default_credentials": self.get_credentials()
        }
        return sftp_config

    def get_host_by_name(self, hostname):
        """
        Information:
            Get a specific host configuration by hostname or IP address.
            Returns the host config merged with default credentials.

        Parameters:
            Input: hostname - The hostname or IP address to search for
            Output: Dictionary containing the host configuration or None if not found

        Date: 03/06/2025
        Author: TOVY
        """
        hosts = self.get_sftp_hosts()
        for host in hosts:
            if (host.get('hostname') == hostname or 
                host.get('ip_address') == hostname):
                return host
        return None

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
            First searches in plc.yaml, then in config.yaml.
            Safely retrieves configuration values with a fallback default.

        Parameters:
            Input: param - The parameter name to look up in the configuration
                  default - The default value to return if param is not found
            Output: The value of the parameter or the default value if not found

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            # First try primary config (plc.yaml)
            if param in self.config:
                return self.config.get(param, default)
            
            # Then try secondary config (config.yaml)
            if param in self.secondary_config:
                return self.secondary_config.get(param, default)
            
            return default
        except (AttributeError, TypeError) as e:
            print(f"Error accessing configuration parameter '{param}': {e}")
            return default

    def save_config(self, yaml_content, yaml_path=None):
        """
        Information:
            Save the provided YAML content to a file.
            Validates the YAML format before saving and updates the internal configuration.
            Uses the original path if no new path is provided.
            Only saves to the primary config file (plc.yaml).

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
            if test_config is None:
                test_config = {}
            
            # Write to file
            with open(path, "w") as file:
                file.write(yaml_content)
                
            # Update the internal config with new content (only primary config)
            if path == self.yaml_path:
                self.config = test_config
                
                # Reload secondary config to ensure consistency
                if os.path.exists(self.config_yaml_path):
                    try:
                        with open(self.config_yaml_path, "r") as f:
                            self.secondary_config = yaml.safe_load(f) or {}
                    except Exception as e:
                        print(f"Warning: Could not reload config.yaml: {e}")
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {str(e)}")

    def save_secondary_config(self, config_data):
        """
        Information:
            Save configuration data to the secondary config file (config.yaml).
            Useful for updating database credentials or other secondary settings.

        Parameters:
            Input: config_data - Dictionary containing configuration data to save
            Output: True if successful, raises exception otherwise

        Date: 03/06/2025
        Author: TOVY
        """
        try:
            with open(self.config_yaml_path, "w") as file:
                yaml.dump(config_data, file, default_flow_style=False, indent=2)
            
            # Update internal secondary config
            self.secondary_config = config_data or {}
            print(f"Secondary config saved to: {self.config_yaml_path}")
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to save secondary configuration: {str(e)}")

    def get_all_config_info(self):
        """
        Information:
            Get a summary of all loaded configuration information.
            Useful for debugging and verification.

        Parameters:
            Output: Dictionary containing information about loaded configs

        Date: 03/06/2025
        Author: TOVY
        """
        return {
            "primary_config_path": self.yaml_path,
            "secondary_config_path": self.config_yaml_path,
            "primary_config_loaded": bool(self.config),
            "secondary_config_loaded": bool(self.secondary_config),
            "has_database_config": "database" in self.secondary_config or "database" in self.config,
            "has_sftp_hosts": "sftp_hosts" in self.config,
            "has_credentials": any(key in self.secondary_config for key in ["username", "password"]),
            "database_config": self.get_database_info() if ("database" in self.secondary_config or "database" in self.config) else None,
            "sftp_config": self.get_sftp_config()
        }