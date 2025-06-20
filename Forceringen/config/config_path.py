import os
from Forceringen.util.config_manager import ConfigLoader


class ConfigPath:
    """Central configuration path management"""

    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.yaml_path = os.path.abspath(os.path.join(script_dir, "..", "config", "plc.yaml"))

    def get_path(self):
        return self.yaml_path

    def create_config_loader(self):
        """Factory method to create ConfigLoader with the correct path"""
        return ConfigLoader(str(self.yaml_path))


# Create global instance
config_path = ConfigPath()

# Your existing code using the class
try:
    config_loader = config_path.create_config_loader()
    config = config_loader.config  # Store for backward compatibility
    host_options = config_loader.get_host_options()
except FileNotFoundError:
    raise RuntimeError(
        f"YAML config file not found: {config_path.get_path()}\n"
        "Please make sure 'plc.yaml' exists in the group work folder next to this script."
    )