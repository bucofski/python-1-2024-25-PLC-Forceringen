import yaml
import psycopg2


def sync_plc_resources_from_yaml(yaml_path, conn):
    # 1. Load all PLC/resource combinations from YAML
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    plc_resources = []
    for host in config.get("sftp_hosts", []):
        plc = host.get('hostname')
        resources = host.get('resources', [])
        for resource in resources:
            plc_resources.append({'PLC': plc, 'resource': resource})

    # 2. Upsert all current PLC/resources, and keep for "keep" set
    with conn:
        with conn.cursor() as cur:
            for pair in plc_resources:
                cur.execute("""
                            INSERT INTO plc_resource_table (plc, resource)
                            VALUES (%(PLC)s, %(resource)s) ON CONFLICT (plc, resource) DO NOTHING
                            """, pair)

            # 3. Delete any PLC/resources not in the YAML
            # Convert to a set of (plc, resource) tuples for easy comparison
            key_tuples = set((item['PLC'], item['resource']) for item in plc_resources)
            # Prepare the values for deletion (if key_tuples is empty, skip delete)
            if key_tuples:
                # Use NOT IN for deletion
                delete_sql = """
                             DELETE
                             FROM plc_resource_table
                             WHERE (plc, resource) NOT IN (SELECT unnest(%s::text[]), unnest(%s::text[])) \
                             """
                plc_list, resource_list = zip(*key_tuples)
                cur.execute(delete_sql, (list(plc_list), list(resource_list)))
            else:
                # If no valid pairs in YAML, clear the table
                cur.execute("DELETE FROM plc_resource_table;")


# ====== USAGE EXAMPLE ======

conn = psycopg2.connect(
    dbname="<your_db>", user="<your_user>", password="<your_password>", host="<your_host>"
)
conn.close()

if __name__ == "__main__":
    sync_plc_resources_from_yaml("plc.yaml", conn)
