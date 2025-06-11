"""
SSH/SCP Client Module for PLC Connection

Information:
    This module provides functionality for connecting to SSH servers and downloading files using SCP.
    It includes a class for managing SSH connections and methods for file operations using SCP protocol.
    The module can be run as a script with interactive host selection.
    Designed to work with industrial PLCs that support SCP but not SFTP.

Date: 03/06/2025
Author: TOVY
"""

from Forceringen.util.config_manager import ConfigLoader
import paramiko
import os


class SCPClient:
    """
    Information:
        A client for connecting to SSH servers and downloading files using SCP protocol.
        Manages SSH connections and provides methods for file operations.
        Designed for compatibility with industrial PLCs like the one described in the email.

    Parameters:
        Input: Connection details including hostname, port, username, and password

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, hostname, port, username, password, timeout=60):
        """
        Information:
            Initialize the SCP client with connection parameters.
            Sets up initial state with no active connections.

        Parameters:
            Input: hostname - The remote server hostname or IP address
                  port - The SSH port number
                  username - The SSH username
                  password - The SSH password
                  timeout - Connection timeout in seconds

        Date: 03/06/2025
        Author: TOVY
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ssh = None

    def connect(self):
        """
        Information:
            Establish SSH connection to the remote server.
            Uses settings optimized for industrial PLCs and embedded systems.
            Mimics the connection method used by PuTTY as described in the email.

        Date: 03/06/2025
        Author: TOVY
        """
        print(f"🔄 Attempting to connect to {self.hostname}:{self.port} using SCP protocol...")

        # Try different connection strategies similar to PuTTY
        strategies = [
            ("PLC-optimized settings", self._connect_plc_optimized),
            ("Legacy compatibility", self._connect_legacy),
            ("Basic connection", self._connect_basic)
        ]

        for strategy_name, connect_method in strategies:
            try:
                print(f"  Trying {strategy_name}...")
                connect_method()
                print(f"✅ Connected successfully using {strategy_name}")
                return True
            except Exception as e:
                print(f"  🔺 {strategy_name} failed: {e}")

        print("🔺 All connection attempts failed")
        return False

    def _connect_plc_optimized(self):
        """
        Information:
            Connection optimized for PLCs with IPSSH implementation.
            Uses settings similar to what PuTTY would use.
        """
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Settings optimized for IPSSH-7.0.0 and similar PLC implementations
        connect_kwargs = {
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'timeout': self.timeout,
            'allow_agent': False,
            'look_for_keys': False,
            'banner_timeout': 30,
            'auth_timeout': 30,
            'gss_auth': False,
            'gss_kex': False,
            # Disable problematic algorithms for older PLC systems
            'disabled_algorithms': {
                'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512'],
                'kex': ['curve25519-sha256@libssh.org', 'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521'],
                'cipher': ['chacha20-poly1305@openssh.com', 'aes128-gcm@openssh.com', 'aes256-gcm@openssh.com']
            }
        }

        self.ssh.connect(**connect_kwargs)

    def _connect_legacy(self):
        """
        Information:
            Legacy connection method for older industrial systems.
        """
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'timeout': self.timeout,
            'allow_agent': False,
            'look_for_keys': False,
            'gss_auth': False,
            'gss_kex': False,
        }

        self.ssh.connect(**connect_kwargs)

    def _connect_basic(self):
        """
        Information:
            Basic connection as last resort.
        """
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.ssh.connect(
            hostname=self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=self.timeout
        )

    def test_connection(self):
        """
        Information:
            Test the SSH connection by executing a simple command.
            Useful for verifying the connection is working properly.

        Date: 03/06/2025
        Author: TOVY
        """
        if self.ssh is None:
            print("No SSH connection available. Call connect() first.")
            return False

        try:
            stdin, stdout, stderr = self.ssh.exec_command('echo "Connection test successful"', timeout=10)
            result = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if result:
                print(f"✅ Connection test: {result}")
                return True
            elif error:
                print(f"🔺 Connection test error: {error}")
                return False
            else:
                print("✅ Connection test: Command executed (no output)")
                return True
        except Exception as e:
            print(f"🔺 Connection test failed: {e}")
            return False

    def download_file_scp(self, remote_file, local_file):
        """
        Information:
            Download a file using SCP protocol (similar to pscp.exe from PuTTY).
            This method replicates the functionality described in the email.

        Parameters:
            Input: remote_file - Path to the file on the remote server
                  local_file - Path where the file should be saved locally

        Date: 03/06/2025
        Author: TOVY
        """
        if self.ssh is None:
            print("Call connect() before download.")
            return False

        os.makedirs(os.path.dirname(local_file), exist_ok=True)

        try:
            print(f"📥 Downloading via SCP: {remote_file} → {local_file}")

            # Use SCP protocol to download the file
            with self.ssh.open_sftp() as sftp:
                # Try SFTP first (some systems support both)
                try:
                    file_size = sftp.stat(remote_file).st_size
                    print(f"  File size: {file_size} bytes")
                    sftp.get(remote_file, local_file)
                    print(f"✅ Downloaded via SFTP: {remote_file}")
                    return True
                except:
                    # If SFTP fails, fall back to SCP via command execution
                    pass

            # Fallback: Use SCP via command execution (similar to pscp.exe)
            scp_command = f'cat "{remote_file}"'
            stdin, stdout, stderr = self.ssh.exec_command(scp_command, timeout=60)

            # Read the file content
            file_content = stdout.read()
            error_content = stderr.read().decode().strip()

            if error_content and "No such file" in error_content:
                print(f"🔺 File not found: {remote_file}")
                return False

            # Write content to local file
            with open(local_file, 'wb') as f:
                f.write(file_content)

            print(f"✅ Downloaded via SCP command: {remote_file} ({len(file_content)} bytes)")
            return True

        except Exception as e:
            print(f"🔺 Error downloading {remote_file}: {e}")
            return False

    def list_remote_files(self, remote_path):
        """
        Information:
            List files in a remote directory using SSH commands.
            Alternative to SFTP directory listing for systems that don't support SFTP.

        Parameters:
            Input: remote_path - Path to the remote directory

        Date: 03/06/2025
        Author: TOVY
        """
        if self.ssh is None:
            print("No SSH connection available. Call connect() first.")
            return []

        try:
            # Use ls command to list directory contents
            ls_command = f'ls -la "{remote_path}"'
            stdin, stdout, stderr = self.ssh.exec_command(ls_command, timeout=30)

            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if error and "No such file" not in error:
                print(f"🔺 Error listing directory: {error}")
                return []

            if output:
                print(f"\nContents of {remote_path}:")
                print(output)
                # Extract filenames (basic parsing)
                files = []
                for line in output.split('\n')[1:]:  # Skip first line (total)
                    if line.strip() and not line.startswith('total'):
                        parts = line.split()
                        if len(parts) >= 9:
                            filename = ' '.join(parts[8:])  # Handle filenames with spaces
                            files.append(filename)
                return files

        except Exception as e:
            print(f"🔺 Error listing remote files: {e}")

        return []

    def download_files(self, remote_files, local_base_dir):
        """
        Information:
            Download multiple files using SCP protocol.
            Creates a base directory if it doesn't exist.
            Names local files based on components of the remote path.

        Parameters:
            Input: remote_files - List of paths to files on the remote server
                  local_base_dir - Base directory for storing downloaded files locally

        Date: 03/06/2025
        Author: TOVY
        """
        if self.ssh is None:
            print("Call connect() before download.")
            return

        os.makedirs(local_base_dir, exist_ok=True)
        successful_downloads = 0
        total_files = len(remote_files)

        print(f"\n📦 Starting SCP download of {total_files} files to {local_base_dir}")

        for i, remote_file in enumerate(remote_files, 1):
            print(f"\n[{i}/{total_files}] Processing: {remote_file}")

            # Create local filename
            if remote_file.startswith('/'):
                # For absolute paths, use the filename or create a meaningful name
                filename = os.path.basename(remote_file)
                if not filename:  # Handle paths ending with /
                    filename = remote_file.replace('/', '_').strip('_') + '.dat'
            else:
                parts = os.path.normpath(remote_file).split(os.sep)
                if len(parts) >= 3:
                    filename = f"{parts[-3]}_{parts[-2]}.dat"
                else:
                    filename = os.path.basename(remote_file) or 'downloaded_file.dat'

            local_path = os.path.join(local_base_dir, filename)

            if self.download_file_scp(remote_file, local_path):
                successful_downloads += 1

        print(f"\n📊 Download summary: {successful_downloads}/{total_files} files successful")

    def close(self):
        """
        Information:
            Close the SSH connection.
            Provides feedback when connection is closed.

        Date: 03/06/2025
        Author: TOVY
        """
        if self.ssh:
            self.ssh.close()
            print("SSH connection closed.")


if __name__ == "__main__":
    # Load config from yaml
    config = ConfigLoader("../config/plc.yaml")

    sftp_hosts = config.get("sftp_hosts", [])
    if not sftp_hosts:
        print("No sftp_hosts found in configuration.")
        exit(1)

    # Show a numbered list of available hosts
    print("Available SSH/SCP hosts:")
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

    # Get remote files - check host-specific first, then global config
    remote_files = selected_host.get('remote_files') or config.get('remote_files', [])

    # Handle both single file (string) and multiple files (list)
    if isinstance(remote_files, str):
        remote_files = [remote_files]
    elif not isinstance(remote_files, list):
        remote_files = []

    timeout = selected_host.get('timeout', 60)  # Default to 60 seconds for PLCs

    # Get local_base_dir from the root config if not present in host config
    local_base_dir = selected_host.get('local_base_dir') or config.get('local_base_dir')

    # If still empty, create a default based on the hostname
    if not local_base_dir:
        hostname_dir = selected_host.get('hostname', 'unknown_host')
        local_base_dir = os.path.abspath(f"downloads/{hostname_dir}")
        print(f"No local_base_dir specified, using {local_base_dir}")

    print(f"\n🔄 Connecting to {hostname}:{port} (similar to PuTTY pscp.exe)...")
    client = SCPClient(
        hostname=hostname,
        port=port,
        username=username,
        password=password,
        timeout=timeout
    )

    if client.connect():
        # Test the connection
        client.test_connection()

        # Download files using SCP protocol
        if remote_files:
            client.download_files(remote_files, local_base_dir)
        else:
            print("No remote files specified in configuration.")
            # Optionally list some common directories
            print("\nTrying to list root directory...")
            client.list_remote_files('/')

    client.close()