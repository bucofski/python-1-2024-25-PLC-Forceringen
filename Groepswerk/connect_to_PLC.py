import paramiko


def ssh_sftp_download(hostname, port, username, password, remote_file, local_file):
    # Create an SSH client object
    ssh = paramiko.SSHClient()

    # Automatically add the server's host key (if not already in known_hosts)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the remote host on the specified port
        ssh.connect(hostname=hostname, port=port, username=username, password=password)
        print(f"Connected to {hostname} on port {port}")

        # Create an SFTP session from the open SSH connection
        sftp = ssh.open_sftp()

        # Download a file from the remote server
        sftp.get(remote_file, local_file)
        print(f"Downloaded remote file {remote_file} to local file {local_file}")

        # Close the SFTP session
        sftp.close()

    except paramiko.AuthenticationException:
        print("Authentication failed, please verify your credentials")
    except paramiko.SSHException as e:
        print(f"Unable to establish SSH connection: {e}")
    except Exception as e:
        print(f"Exception occurred: {e}")
    finally:
        # Close the SSH connection
        ssh.close()


# Example usage - replace with your values
ssh_sftp_download('192.168.0.58',
                  22,
                  'pi',
                  'raspberry',
                  'Documents/test/for.dat',
                  '/python-1-2024-25-PLC-Forceringen/TDS.dat'
                  )


if __name__ == "__main__":
    print(ssh_sftp_download)
