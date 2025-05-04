import yaml
import os
from connect_to_PLC import SFTPClient
from class_making_querry import FileReader, DataProcessor
from class_database import DatabaseSearcher
from class_bit_conversion import BitConversion
from datetime import datetime
import re


def select_sftp_host(config):
    sftp_hosts = config.get("sftp_hosts", [])
    if not sftp_hosts:
        print("No sftp_hosts found in configuration.")
        return None

    print("Available SFTP hosts:")
    for idx, host in enumerate(sftp_hosts, 1):
        disp_name = host.get('hostname', host.get('ip_address'))
        print(f"{idx}. {disp_name} ({host.get('ip_address', 'no IP')})")

    while True:
        try:
            selection = int(input(f"Select a host to connect (1-{len(sftp_hosts)}): "))
            if 1 <= selection <= len(sftp_hosts):
                break
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")
    return sftp_hosts[selection - 1]


def main():
    start = datetime.now()
    # Step 1: Load YAML and select SFTP host
    with open("plc.yaml", "r") as f:
        config = yaml.safe_load(f)

    host_cfg = select_sftp_host(config)
    if host_cfg is None:
        return

    hostname = host_cfg.get('ip_address', host_cfg.get('hostname'))
    port = host_cfg['port']
    username = host_cfg['username']
    password = host_cfg['password']
    remote_files = host_cfg.get('remote_files', [])
    local_base_dir = host_cfg.get('local_base_dir', '')

    # Step 2: Download files over SFTP
    client = SFTPClient(hostname, port, username, password)
    client.connect()
    client.download_files(remote_files, local_base_dir)
    client.close()

    # Step 3: Process each downloaded file
    # (Assume you want to process all .dat files in local_base_dir)
    for filename in os.listdir(local_base_dir):
        if filename.endswith(".dat"):
            local_file_path = os.path.join(local_base_dir, filename)
            print(f"\n--- Processing {local_file_path} ---")
            file_reader = FileReader(local_file_path)
            words_list = file_reader.read_and_parse_file()
            processed_list = list(DataProcessor.convert_and_process_list(words_list))

            # Step 4: Database search
            # Adjust DB path as needed
            db_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"

            def extract_table_from_filename(filename):
                # Assumes filename format: ANYTHING_TABLENAME.dat
                match = re.match(r".*_(.*?)\.dat$", filename, re.IGNORECASE)
                return match.group(1).upper() if match else None

            table_name = extract_table_from_filename(filename)
            if not table_name:
                raise ValueError("Could not extract table name.")

            custom_query = f"SELECT *, SecondComment FROM {table_name} WHERE Name IN ({{placeholders}})"
            with DatabaseSearcher(db_path) as searcher:
                results = searcher.search(processed_list, query_template=custom_query)

            # Step 5: Bit Conversion
            bit_converter = BitConversion(results)
            common_elements = bit_converter.convert_variable_list()

            # Step 6: Print results2
            for sublist in common_elements:
                print(sublist)

    end = datetime.now()
    print(f"\nTime taken: {(end - start).total_seconds()} seconds")


if __name__ == "__main__":
    main()
