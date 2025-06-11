"""
Enhanced SFTP Client Module with PuTTY-style Functionality

Information:
    This module provides functionality for connecting to SFTP servers and downloading files.
    It includes PuTTY-style command execution and file transfer capabilities.
    The module can be run as a script with interactive host selection or direct commands.

Date: 11/06/2025
Author: TOVY (Enhanced)
"""

from Forceringen.util.config_manager import ConfigLoader
import paramiko
import os
import sys
import argparse


class EnhancedSFTPClient:
    """
    Information:
        An enhanced client for connecting to SFTP servers with PuTTY-style functionality.
        Manages SSH and SFTP connections and provides methods for file operations and command execution.

    Parameters:
        Input: Connection details including hostname, port, username, and password

    Date: 11/06/2025
    Author: TOVY (Enhanced)
    """

    def __init__(self, hostname, port, username, password):
        """
        Information:
            Initialize the enhanced SFTP client with connection parameters.
            Sets up initial state with no active connections.

        Parameters:
            Input: hostname - The remote server hostname or IP address
                  port - The SSH port number
                  username - The SSH username
                  password - The SSH password

        Date: 11/06/2025
        Author: TOVY (Enhanced)
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

        Date: 11/06/2025
        Author: TOVY (Enhanced)
        """
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(
                hostname=self.hostname, port=self.port,
                username=self.username, password=self.password,
                timeout=10
            )
            self.sftp = self.ssh.open_sftp()
            print(f"✅ Connected to {self.hostname}:{self.port}")
            return True
        except Exception as e:
            print(f"🔺 Connection error: {e}")
            return False

    def execute_command(self, command):
        """
        Information:
            Execute a command on the remote server via SSH.
            Returns the command output and error streams.

        Parameters:
            Input: command - The command to execute on the remote server

        Returns:
            Tuple of (stdout, stderr, exit_status)

        Date: 11/06/2025
        Author: TOVY (Enhanced)
        """
        if self.ssh is None:
            print("❌ SSH connection not established. Call connect() first.")
            return None, None, -1

        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            return stdout_data, stderr_data, exit_status
        except Exception as e:
            print(f"🔺 Command execution error: {e}")
            return None, str(e), -1

    def putty_style_copy(self, remote_file, local_file=None):
        """
        Information:
            Copy a file from remote server to local directory using PuTTY-style approach.
            Similar to: pscp.exe -P 22000 -pw password user@host:/path/file ./

        Parameters:
            Input: remote_file - Path to the file on the remote server
                  local_file - Optional local file path (defaults to current directory)

        Date: 11/06/2025
        Author: TOVY (Enhanced)
        """
        if local_file is None:
            # Extract filename from remote path and save to current directory
            local_file = os.path.basename(remote_file)

        return self.download_file(remote_file, local_file)

    def download_file(self, remote_file, local_file):
        """
        Information:
            Download a remote file to a local path.
            Creates the necessary directories if they don't exist.
            Provides feedback on download status.

        Parameters:
            Input: remote_file - Path to the file on the remote server
                  local_file - Path where the file should be saved locally

        Date: 11/06/2025
        Author: TOVY (Enhanced)
        """
        if self.sftp is None:
            print("❌ SFTP connection not established. Call connect() first.")
            return False

        # Create directory if it doesn't exist
        local_dir = os.path.dirname(local_file)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        try:
            # Check if remote file exists
            try:
                self.sftp.stat(remote_file)
            except FileNotFoundError:
                print(f"❌ Remote file not found: {remote_file}")
                return False

            self.sftp.get(remote_file, local_file)
            file_size = os.path.getsize(local_file)
            print(f"✅ Downloaded {remote_file} → {local_file} ({file_size} bytes)")
            return True
        except Exception as e:
            print(f"🔺 Error downloading {remote_file}: {e}")
            return False

    def list_directory(self, remote_path="."):
        """
        Information:
            List contents of a remote directory.

        Parameters:
            Input: remote_path - Path to list on the remote server

        Date: 11/06/2025
        Author: TOVY (Enhanced)
        """
        if self.sftp is None:
            print("❌ SFTP connection not established. Call connect() first.")
            return []

        try:
            files = self.sftp.listdir_attr(remote_path)
            print(f"\n📁 Directory listing for {remote_path}:")
            print("-" * 60)
            for file_attr in files:
                file_type = "📁" if file_attr.st_mode and (file_attr.st_mode & 0o040000) else "📄"
                size = file_attr.st_size if file_attr.st_size else 0
                print(f"{file_type} {file_attr.filename:<30} {size:>10} bytes")
            return [f.filename for f in files]
        except Exception as e:
            print(f"🔺 Error listing directory {remote_path}: {e}")
            return []

    def download_files(self, remote_files, local_base_dir):
        """
        Information:
            Download multiple files with dynamic local naming.
            Creates a base directory if it doesn't exist.
            Names local files based on components of the remote path.

        Parameters:
            Input: remote_files - List of paths to files on the remote server
                  local_base_dir - Base directory for storing downloaded files locally

        Date: 11/06/2025
        Author: TOVY (Enhanced)
        """
        if self.sftp is None:
            print("❌ SFTP connection not established. Call connect() first.")
            return

        os.makedirs(local_base_dir, exist_ok=True)
        successful_downloads = 0

        for remote_file in remote_files:
            parts = os.path.normpath(remote_file).split(os.sep)
            if len(parts) < 3:
                print(f"⚠️  Path '{remote_file}' doesn't have enough levels.")
                continue

            local_name = f"{parts[-3]}_{parts[-2]}.dat"
            local_path = os.path.join(local_base_dir, local_name)

            if self.download_file(remote_file, local_path):
                successful_downloads += 1

        print(f"\n📊 Summary: {successful_downloads}/{len(remote_files)} files downloaded successfully")

    def close(self):
        """
        Information:
            Close the SFTP and SSH connections.
            Provides feedback when connections are closed.

        Date: 11/06/2025
        Author: TOVY (Enhanced)
        """
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print("🔌 Connections closed.")


def putty_pscp_style_command(hostname, port, username, password, remote_file, local_file=None):
    """
    Information:
        Execute a PuTTY PSCP-style command programmatically.
        Equivalent to: pscp.exe -P port -pw password user@host:remote_file local_file

    Parameters:
        Input: Connection parameters and file paths

    Date: 11/06/2025
    Author: TOVY (Enhanced)
    """
    client = EnhancedSFTPClient(hostname, port, username, password)

    if not client.connect():
        return False

    try:
        success = client.putty_style_copy(remote_file, local_file)
        return success
    finally:
        client.close()


def main():
    """
    Information:
        Main function with command-line interface support.
        Supports both interactive mode and direct command execution.

    Date: 11/06/2025
    Author: TOVY (Enhanced)
    """
    parser = argparse.ArgumentParser(description='Enhanced SFTP Client with PuTTY-style functionality')
    parser.add_argument('--host', help='Hostname or IP address')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--user', help='SSH username')
    parser.add_argument('--password', help='SSH password')
    parser.add_argument('--remote-file', help='Remote file path to download')
    parser.add_argument('--local-file', help='Local file path (optional)')
    parser.add_argument('--list-dir', help='List remote directory contents')
    parser.add_argument('--command', help='Execute command on remote server')

    args = parser.parse_args()

    # If command line arguments provided, use direct mode
    if args.host and args.user and args.password:
        client = EnhancedSFTPClient(args.host, args.port, args.user, args.password)

        if not client.connect():
            sys.exit(1)

        try:
            if args.remote_file:
                client.putty_style_copy(args.remote_file, args.local_file)
            elif args.list_dir:
                client.list_directory(args.list_dir)
            elif args.command:
                stdout, stderr, exit_code = client.execute_command(args.command)
                if stdout:
                    print("STDOUT:", stdout)
                if stderr:
                    print("STDERR:", stderr)
                print(f"Exit code: {exit_code}")
        finally:
            client.close()
        return

    # Interactive mode using config file
    try:
        config = ConfigLoader("../config/plc.yaml")
    except Exception as e:
        print(f"🔺 Error loading config: {e}")
        print("💡 You can also use command line arguments. Use --help for details.")
        sys.exit(1)

    sftp_hosts = config.get("sftp_hosts", [])
    if not sftp_hosts:
        print("❌ No sftp_hosts found in configuration.")
        sys.exit(1)

    # Show available hosts
    print("🖥️  Available SFTP hosts:")
    for idx, host in enumerate(sftp_hosts, 1):
        disp_name = host.get('hostname', host.get('ip_address'))
        print(f"{idx}. {disp_name} ({host.get('ip_address', 'no IP')})")

    # Host selection
    while True:
        try:
            selection = int(input(f"\n🎯 Select a host to connect (1-{len(sftp_hosts)}): "))
            if 1 <= selection <= len(sftp_hosts):
                break
            else:
                print("❌ Invalid selection.")
        except ValueError:
            print("❌ Please enter a number.")

    selected_host = sftp_hosts[selection - 1]
    hostname = selected_host.get('ip_address', selected_host.get('hostname'))
    port = selected_host['port']
    username = selected_host['username']
    password = selected_host['password']
    remote_files = selected_host.get('remote_files', [])

    # Get local_base_dir
    local_base_dir = selected_host.get('local_base_dir') or config.get('local_base_dir')
    if not local_base_dir:
        hostname_dir = selected_host.get('hostname', 'unknown_host')
        local_base_dir = os.path.abspath(f"downloads/{hostname_dir}")
        print(f"💡 No local_base_dir specified, using {local_base_dir}")

    print(f"\n🔗 Connecting to {hostname} ({selected_host.get('hostname')})...")
    client = EnhancedSFTPClient(hostname, port, username, password)

    if not client.connect():
        sys.exit(1)

    try:
        # Interactive menu
        while True:
            print("\n📋 Available actions:")
            print("1. Download configured files")
            print("2. Download specific file (PuTTY style)")
            print("3. List remote directory")
            print("4. Execute remote command")
            print("5. Exit")

            choice = input("\n🎯 Select action (1-5): ").strip()

            if choice == '1':
                if remote_files:
                    client.download_files(remote_files, local_base_dir)
                else:
                    print("❌ No remote files configured for this host.")

            elif choice == '2':
                remote_file = input("📄 Enter remote file path: ").strip()
                local_file = input("💾 Enter local file path (or press Enter for current directory): ").strip()
                if not local_file:
                    local_file = None
                client.putty_style_copy(remote_file, local_file)

            elif choice == '3':
                remote_path = input("📁 Enter remote directory path (or press Enter for current): ").strip()
                if not remote_path:
                    remote_path = "."
                client.list_directory(remote_path)

            elif choice == '4':
                command = input("⚡ Enter command to execute: ").strip()
                stdout, stderr, exit_code = client.execute_command(command)
                if stdout:
                    print(f"📤 STDOUT:\n{stdout}")
                if stderr:
                    print(f"📤 STDERR:\n{stderr}")
                print(f"📊 Exit code: {exit_code}")

            elif choice == '5':
                break

            else:
                print("❌ Invalid choice.")

    finally:
        client.close()


if __name__ == "__main__":
    main()