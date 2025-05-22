import yaml
import paramiko
import os


class SFTPClient:
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ssh = None
        self.sftp = None

    def connect(self):
        """Establish SSH and SFTP connection."""
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
            print(f"Connection error: {e}")

    def download_file(self, remote_file, local_file):
        """Download a remote file to a local path, creating directories if needed."""
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
        """Download multiple files with dynamic local naming, creating base dir if needed."""
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
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print("Connections closed.")


if __name__ == "__main__":
    # Load config from yaml
    with open("plc.yaml", "r") as f:
        config = yaml.safe_load(f)

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
    remote_files = selected_host.get('remote_files', [])

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
