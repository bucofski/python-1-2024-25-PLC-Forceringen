import paramiko
import os


class SFTPClient:
    def __init__(self, hostname, port, username, password):
        """
        Initializes the SFTPClient with connection details.

        :param hostname: The hostname or IP address of the SSH server.
        :param port: The port number for SSH connection.
        :param username: The SSH username.
        :param password: The SSH password.
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ssh = None
        self.sftp = None

    def connect(self):
        """Establishes an SSH and SFTP connection."""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.ssh.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password
            )
            print(f"Connected to {self.hostname} on port {self.port}")
            self.sftp = self.ssh.open_sftp()
        except paramiko.AuthenticationException:
            print("Authentication failed, please verify your credentials")
        except paramiko.SSHException as e:
            print(f"Unable to establish SSH connection: {e}")
        except Exception as e:
            print(f"Exception occurred: {e}")

    def download_file(self, remote_file, local_file):
        """
        Downloads a single file from the remote server to the local machine.
        Ensures that the local directory exists; if not, it creates it.

        :param remote_file: The path to the file on the remote server.
        :param local_file: The path where the file will be saved locally.
        """
        if self.sftp is None:
            print("SFTP connection not established. Call connect() first.")
            return

        # Extract the directory from the local file path
        local_dir = os.path.dirname(local_file)
        if local_dir and not os.path.exists(local_dir):
            try:
                os.makedirs(local_dir, exist_ok=True)
                print(f"Created local directory: {local_dir}")
            except OSError as e:
                print(f"Failed to create directory {local_dir}: {e}")
                return

        try:
            self.sftp.get(remote_file, local_file)
            print(f"Downloaded {remote_file} to {local_file}")
        except FileNotFoundError:
            print(f"Remote file {remote_file} does not exist.")
        except Exception as e:
            print(f"Failed to download file: {e}")

    def download_files(self, remote_files, local_base_dir):
        """
        Downloads multiple files from the remote server to the local machine.
        Each local file is named based on its directory structure, e.g.,
        'Btest/Btest/for.dat' becomes 'Btest_Btest.dat'.

        :param remote_files: A list of remote file paths to download.
        :param local_base_dir: The base directory on the local machine where files will be saved.
        """
        if self.sftp is None:
            print("SFTP connection not established. Call connect() first.")
            return

        # Ensure the local base directory exists
        if not os.path.exists(local_base_dir):
            try:
                os.makedirs(local_base_dir, exist_ok=True)
                print(f"Created base local directory: {local_base_dir}")
            except OSError as e:
                print(f"Failed to create base directory {local_base_dir}: {e}")
                return

        for remote_file in remote_files:
            try:
                # Normalize the remote file path
                normalized_remote = os.path.normpath(remote_file)

                # Split the path into parts
                path_parts = normalized_remote.split(os.sep)

                # Ensure there are at least two directories in the path
                if len(path_parts) < 3:
                    print(f"Remote file path '{remote_file}' does not have enough directory levels.")
                    continue

                # Extract the first and second directory names
                first_dir = path_parts[-3]
                second_dir = path_parts[-2]

                # Construct the local file name as <first_dir>_<second_dir>.dat
                local_file_name = f"{first_dir}_{second_dir}.dat"
                local_file_path = os.path.join(local_base_dir, local_file_name)

                # Download the file
                self.download_file(remote_file, local_file_path)

            except Exception as e:
                print(f"Error processing {remote_file}: {e}")

    def close(self):
        """Closes the SFTP and SSH connections."""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print("Connections closed.")


# Example usage
if __name__ == "__main__":
    # Initialize the SFTP client with your credentials
    client = SFTPClient(
        hostname='192.168.0.217',
        port=22,
        username='pi',
        password='raspberry'
    )

    # Establish the connection
    client.connect()

    # List of remote files to download
    remote_files = [
        '/home/pi/Btest/NIET/for.dat',
        '/home/pi/Btest/TDS/for.dat',
    ]

    # Define the base local directory where files will be saved
    local_base_dir = '/python-1-2024-25-PLC-Forceringen/'

    # Download multiple files with dynamic naming
    client.download_files(remote_files, local_base_dir)

    # Close the connection
    client.close()
