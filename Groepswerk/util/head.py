import os
import asyncio
from Groepswerk.PLC.connect_to_PLC import SFTPClient
from Groepswerk.Database.class_making_querry import FileReader, DataProcessor
from Groepswerk.Database.class_database import DatabaseSearcher
from Groepswerk.PLC.class_bit_conversion import BitConversion
from datetime import datetime
from Groepswerk.util.class_config_loader import ConfigLoader
from Groepswerk.Database.class_writes_to_db import BitConversionDBWriter

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
    # # Load YAML and select SFTP host(s)
    # with open("plc.yaml", "r") as f:
    #     config = yaml.safe_load(f)
    #
    # # Load configuration using ConfigLoader instead of direct YAML loading
    config_loader = ConfigLoader("../config/plc.yaml")

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

    end = datetime.now()
    print(f"\nTotal time taken: {(end - start).total_seconds()} seconds")


def run_main_with_host(config_loader, selected_host_name, is_gui_context=False):
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

    # UPDATED: get resources list and construct file paths dynamically
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

    for filename in os.listdir(str(local_base_dir)):
        if filename.endswith(".dat"):
            try:
                plc, resource = filename.replace('.dat', '').split('_', 1)
            except ValueError:
                print(f"Filename '{filename}' does not contain expected '_' separator. Skipping.")
                continue

            table_part = resource  # The table is usually the resource part

            custom_query = f"SELECT *, SecondComment FROM {table_part} WHERE Name IN ({{placeholders}})"
            local_file_path = os.path.join(str(local_base_dir), filename)
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

            # Step 1: Convert and print
            bit_converter = BitConversion(results)
            converted_results = bit_converter.convert_variable_list()
            for sublist in converted_results:
                print(sublist)

            # Step 2: Write using already converted results (no double conversion)
            writer = BitConversionDBWriter(converted_results, config_loader)
            writer.convert_variable_list = lambda: converted_results
    
            if is_gui_context:
                # Use threaded method in GUI context
                print("Writing to database via threading...")
                writer.write_to_database_threaded()
            else:
                # Use the original async approach
                async def run_bit_conversion_and_write():
                    await writer.write_to_database()
            
                # With this:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Create task for background execution
                        task = loop.create_task(run_bit_conversion_and_write())
                        print("Database write task created")
                    else:
                        asyncio.run(run_bit_conversion_and_write())
                except RuntimeError:
                    asyncio.run(run_bit_conversion_and_write())
                    print("Database write task created")


    end = datetime.now()
    print(f"Total time taken: {(end - start).total_seconds()} seconds")

if __name__ == "__main__":
    main()