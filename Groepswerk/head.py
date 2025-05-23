import os
from connect_to_PLC import SFTPClient
from class_making_querry import FileReader, DataProcessor
from class_database import DatabaseSearcher
from class_bit_conversion import BitConversion
from datetime import datetime
from class_config_loader import ConfigLoader
from class_writes_to_db import DataImporter  # Import the DataImporter class


def select_sftp_host(config_loader):
    """Select an SFTP host from the configuration."""
    sftp_hosts = config_loader.get_sftp_hosts()
    if not sftp_hosts:
        print("No sftp_hosts found in configuration.")
        return None

    print("Available SFTP hosts:")
    for i, host in enumerate(sftp_hosts, start=1):
        disp_name = host.get('hostname', host.get('ip_address'))
        print(f"{i}. {disp_name} ({host.get('ip_address', 'no IP')})")
    print("all. Download from all hosts")

    # Create a lookup dictionary for quick hostname access
    hostname_to_host = {host.get('hostname'): host for host in sftp_hosts if 'hostname' in host}

    while True:
        selection = input(f"Type the hostname or 'all' to download from every host: ").strip()
        if selection == "all":
            return "all"
        if selection in hostname_to_host:
            return hostname_to_host[selection]
        else:
            print("Invalid selection. Please try again.")


def main():
    start = datetime.now()

    # Load configuration using ConfigLoader instead of direct YAML loading
    config_loader = ConfigLoader("plc.yaml")

    host_selection = select_sftp_host(config_loader)
    if not host_selection:
        return

    # If user chooses "all", iterate over all hosts:
    if host_selection == "all":
        for host_cfg in config_loader.get_sftp_hosts():
            run_main_with_host(config_loader, host_cfg.get('hostname'))
    else:
        host_cfg = host_selection
        run_main_with_host(config_loader, host_cfg.get('hostname'))

    # Get database configuration from plc.yaml
    db_config = config.get('database', {})
    # Rename 'database' key to 'dbname' if needed for PostgreSQLManager
    if 'database' in db_config:
        db_config['dbname'] = db_config.pop('database')

    # Import processed data to database
    print("\n--- Starting database import ---")
    try:
        # Process each host configuration
        if host_selection == "all":
            hosts_to_process = config.get("sftp_hosts", [])
        else:
            hosts_to_process = [host_cfg]

        for host_cfg in hosts_to_process:
            access_db_path = host_cfg.get('db_path')
            if not access_db_path:
                print(f"Skipping database import for {host_cfg.get('hostname')}: No db_path specified")
                continue

            # Get local directory for this host
            host_name = host_cfg.get('hostname')
            base_local_dir = config.get('local_base_dir', '')
            if base_local_dir and host_name:
                local_base_dir = os.path.join(base_local_dir, host_name)
                if not os.path.exists(local_base_dir):
                    print(f"Skipping database import for {host_name}: Directory {local_base_dir} does not exist")
                    continue

                # Process each .dat file in the directory
                dat_files = [f for f in os.listdir(local_base_dir) if f.endswith('.dat')]
                if not dat_files:
                    print(f"No .dat files found in {local_base_dir}")
                    continue

                for dat_file in dat_files:
                    input_file_path = os.path.join(local_base_dir, dat_file)
                    print(f"\nImporting {dat_file} to database...")
                    importer = DataImporter(db_config)
                    importer.import_data(input_file_path, access_db_path)
                    print(f"✅ Database import completed for {dat_file}")
            else:
                print(f"Skipping database import for {host_name}: Missing local_base_dir or hostname")

    except Exception as e:
        print(f"❌ Database import failed: {e}")

    end = datetime.now()
    print(f"\nTotal time taken: {(end - start).total_seconds()} seconds")


def run_main_with_host(config_loader, selected_host_name):
    start = datetime.now()

    sftp_hosts = config_loader.get_sftp_hosts()
    host_cfg = next((host for host in sftp_hosts if host.get("hostname") == selected_host_name), None)
    if not host_cfg:
        print(f"Host {selected_host_name} not found.")
        return

    hostname = host_cfg.get('ip_address', host_cfg.get('hostname'))
    port = host_cfg['port']
    username = host_cfg['username']
    password = host_cfg['password']

    # Get resources list and construct file paths dynamically
    resources = host_cfg.get('resources', [])
    remote_files = [f"{host_cfg['hostname']}/{resource}/for.dat" for resource in resources]

    base_local_dir = config_loader.get('local_base_dir', '')
    host_name = host_cfg.get('hostname')
    if base_local_dir and host_name:
        local_base_dir = os.path.join(base_local_dir, host_name)
    else:
        print("Error: local_base_dir or hostname is missing in the configuration or selected host.")
        return

    client = SFTPClient(hostname, port, username, password)
    client.connect()
    client.download_files(remote_files, local_base_dir)
    client.close()

    if not os.path.exists(local_base_dir):
        print(f"Error: Local directory '{local_base_dir}' does not exist after download.")
        return

    department_name = config_loader.get("department_name")

    for filename in os.listdir(local_base_dir):
        if filename.endswith(".dat"):
            try:
                plc, resource = filename.replace('.dat', '').split('_', 1)
            except ValueError:
                print(f"Filename '{filename}' does not contain expected '_' separator. Skipping.")
                continue

            table_part = resource  # The table is usually the resource part

            custom_query = f"SELECT *, SecondComment FROM {table_part} WHERE Name IN ({{placeholders}})"
            local_file_path = os.path.join(local_base_dir, filename)
            print(f"\n--- Processing {local_file_path} (table: {table_part}) ---")
            file_reader = FileReader(local_file_path)
            words_list = file_reader.read_and_parse_file()
            processed_list = list(DataProcessor.convert_and_process_list(words_list))

            db_path = host_cfg.get('db_path')
            if not db_path:
                print("Error: db_path not specified for selected host.")
                return
            with DatabaseSearcher(db_path) as searcher:
                results = searcher.search(
                    processed_list,
                    query_template=custom_query,
                    department_name=department_name,
                    plc=plc,
                    resource=resource
                )
            bit_converter = BitConversion(results)
            common_elements = bit_converter.convert_variable_list()
            for sublist in common_elements:
                print(sublist)

    end = datetime.now()
    print(f"\nTime taken: {(end - start).total_seconds()} seconds")


if __name__ == "__main__":
    main()
