"""
SFTP Client Module

Information:
    This module provides functionality for connecting to SFTP servers and downloading files.
    It includes a class for managing SSH/SFTP connections and methods for file operations.
    The module can be run as a script with interactive host selection.

Date: 03/06/2025
Author: TOVY
"""

from Forceringen.util.config_manager import ConfigLoader
import paramiko
import os


class SFTPClient:
    """
    Information:
        A client for connecting to SFTP servers and downloading files.
        Manages SSH and SFTP connections and provides methods for file operations.

    Parameters:
        Input: Connection details including hostname, port, username, and password

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, hostname, port, username, password):
        """
        Information:
            Initialize the SFTP client with connection parameters.
            Sets up initial state with no active connections.

        Parameters:
            Input: hostname - The remote server hostname or IP address
                  port - The SSH port number
                  username - The SSH username
                  password - The SSH password

        Date: 03/06/2025
        Author: TOVY
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ssh = None
        self.sftp = None

    def connect(self):
        """
        Information:
            Establish SSH and SFTP connections to the remote server.
            Uses AutoAddPolicy for accepting unknown host keys.
            Provides feedback on connection status.

        Date: 03/06/2025
        Author: TOVY
        """
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(
                hostname=self.hostname, port=self.port,
                username=self.username, password=self.password
            )
            self.sftp = self.ssh.open_sftp()
            print(f"Connected to {self.hostname}:{self.port}")
        except Exception as e:
            print(f"🔺 Connection error: {e}")

    def download_file(self, remote_file, local_file):
        """
        Information:
            Download a remote file to a local path.
            Creates the necessary directories if they don't exist.
            Provides feedback on download status.

        Parameters:
            Input: remote_file - Path to the file on the remote server
                  local_file - Path where the file should be saved locally

        Date: 03/06/2025
        Author: TOVY
        """
        if self.sftp is None:
            print("Call connect() before download.")
            return
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        try:
            self.sftp.get(remote_file, local_file)
            print(f"Downloaded {remote_file} → {local_file}")
        except Exception as e:
            print(f"Error downloading {remote_file}: {e}")

    def download_files(self, remote_files, local_base_dir):
        """
        Information:
            Download multiple files with dynamic local naming.
            Creates a base directory if it doesn't exist.
            Names local files based on components of the remote path.

        Parameters:
            Input: remote_files - List of paths to files on the remote server
                  local_base_dir - Base directory for storing downloaded files locally

        Date: 03/06/2025
        Author: TOVY
        """
        if self.sftp is None:
            print("Call connect() before download.")
            return
        os.makedirs(local_base_dir, exist_ok=True)

        for remote_file in remote_files:
            parts = os.path.normpath(remote_file).split(os.sep)
            if len(parts) < 3:
                print(f"Path '{remote_file}' doesn't have enough levels.")
                continue
            local_name = f"{parts[-3]}_{parts[-2]}.dat"
            local_path = os.path.join(local_base_dir, local_name)
            self.download_file(remote_file, local_path)

    def close(self):
        """
        Information:
            Close the SFTP and SSH connections.
            Provides feedback when connections are closed.

        Date: 03/06/2025
        Author: TOVY
        """
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print("Connections closed.")


if __name__ == "__main__":
    # Load config from yaml
    config = ConfigLoader("../config/plc.yaml")

    sftp_hosts = config.get("sftp_hosts", [])
    if not sftp_hosts:
        print("No sftp_hosts found in configuration.")
        exit(1)

    # Show a numbered list of available hosts
    print("Available SFTP hosts:")
    for idx, host in enumerate(sftp_hosts, 1):
        disp_name = host.get('hostname', host.get('ip_address'))
        print(f"{idx}. {disp_name} ({host.get('ip_address', 'no IP')})")

    # Ask user to select
    while True:
        try:
            selection = int(input(f"Select a host to connect (1-{len(sftp_hosts)}): "))
            if 1 <= selection <= len(sftp_hosts):
                break
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")

    selected_host = sftp_hosts[selection - 1]
    hostname = selected_host.get('ip_address', selected_host.get('hostname'))
    port = selected_host['port']
    username = selected_host['username']
    password = selected_host['password']
    remote_files = selected_host.get('remote_files') or config.get('remote_files', [])

    # Get local_base_dir from the root config if not present in host config
    local_base_dir = selected_host.get('local_base_dir') or config.get('local_base_dir')

    # If still empty, create a default based on the hostname
    if not local_base_dir:
        hostname_dir = selected_host.get('hostname', 'unknown_host')
        local_base_dir = os.path.abspath(f"downloads/{hostname_dir}")
        print(f"No local_base_dir specified, using {local_base_dir}")

    print(f"\nConnecting to {hostname} ({selected_host.get('hostname')})...")
    client = SFTPClient(
        hostname=hostname,
        port=port,
        username=username,
        password=password,
    )
    client.connect()
    client.download_files(remote_files, local_base_dir)
    client.close()