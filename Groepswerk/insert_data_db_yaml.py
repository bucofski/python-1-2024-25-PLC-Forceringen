import yaml
import psycopg2


def sync_plcs_and_resources(yaml_path, conn):
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    plc_resources = set()
    for host in config.get("sftp_hosts", []):
        plc = host.get('hostname')
        resources = host.get('resources', [])
        for resource in resources:
            plc_resources.add((plc, resource))

    with conn:
        with conn.cursor() as cur:
            # Insert new PLCs
            for plc, _ in plc_resources:
                cur.execute("""
                            INSERT INTO plc (plc_name)
                            VALUES (%s) ON CONFLICT (plc_name) DO NOTHING
                            """, (plc,))

            # Insert new Resources
            for _, resource in plc_resources:
                cur.execute("""
                            INSERT INTO resource (resource_name)
                            VALUES (%s) ON CONFLICT (resource_name) DO NOTHING
                            """, (resource,))

            # Build lookup maps for IDs
            cur.execute("SELECT plc_id, plc_name FROM plc")
            plc_lookup = {name: plc_id for plc_id, name in cur.fetchall()}
            cur.execute("SELECT resource_id, resource_name FROM resource")
            resource_lookup = {name: res_id for res_id, name in cur.fetchall()}

            # Insert/keep associations in join table
            for plc, resource in plc_resources:
                cur.execute("""
                            INSERT INTO plc_resource (plc_id, resource_id)
                            VALUES (%s, %s) ON CONFLICT (plc_id, resource_id) DO NOTHING
                            """, (plc_lookup[plc], resource_lookup[resource]))

            # Delete any association not in the YAML
            if plc_resources:
                # Prepare a string for the VALUES section and corresponding flat tuple list
                values_sql = ",".join(["(%s, %s)"] * len(plc_resources))
                values_flat = []
                for plc, resource in plc_resources:
                    values_flat.extend([plc, resource])

                delete_sql = f"""
                    DELETE FROM plc_resource
                    WHERE NOT (plc_id, resource_id) IN (
                        SELECT p.plc_id, r.resource_id
                        FROM (VALUES {values_sql}) AS v(plc_name, resource_name)
                        JOIN plc p ON v.plc_name = p.plc_name
                        JOIN resource r ON v.resource_name = r.resource_name
                    )
                """
                cur.execute(delete_sql, values_flat)
            else:
                cur.execute("DELETE FROM plc_resource")  # If nothing in YAML, clear all


def get_postgres_connection_info(yaml_path):
    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)
    return config["postgres"]


if __name__ == "__main__":
    yaml_path = "plc.yaml"
    pg_info = get_postgres_connection_info(yaml_path)
    conn = psycopg2.connect(**pg_info)
    sync_plcs_and_resources(yaml_path, conn)
    conn.close()
