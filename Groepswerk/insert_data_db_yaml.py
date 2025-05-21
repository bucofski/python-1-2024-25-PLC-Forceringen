import yaml
import psycopg2


def sync_plcs_and_resources(yaml_path, conn):
    # 1. Parse the PLC/resources from YAML
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
            # 2. Insert PLCs (if not exist)
            for plc, _ in plc_resources:
                cur.execute("""
                            INSERT INTO plc (plc_name)
                            VALUES (%s) ON CONFLICT (plc_name) DO NOTHING
                            """, (plc,))

            # 3. Insert Resources (if not exist)
            for _, resource in plc_resources:
                cur.execute("""
                            INSERT INTO resource (resource_name)
                            VALUES (%s) ON CONFLICT (resource_name) DO NOTHING
                            """, (resource,))

            # 4. Build lookup maps for IDs
            cur.execute("SELECT plc_id, plc_name FROM plc")
            plc_lookup = {name: plc_id for plc_id, name in cur.fetchall()}
            cur.execute("SELECT resource_id, resource_name FROM resource")
            resource_lookup = {name: res_id for res_id, name in cur.fetchall()}

            # 5. Insert/keep associations in join table
            for plc, resource in plc_resources:
                cur.execute("""
                            INSERT INTO plc_resource (plc_id, resource_id)
                            VALUES (%s, %s) ON CONFLICT (plc_id, resource_id) DO NOTHING
                            """, (plc_lookup[plc], resource_lookup[resource]))

            # 6. Delete any association not in the YAML
            # (delete all from plc_resource not in the new set)
            if plc_resources:
                cur.execute("""
                            DELETE
                            FROM plc_resource
                            WHERE NOT (
                                (plc_id, resource_id) IN (SELECT p.plc_id,
                                                                 r.resource_id
                                                          FROM (VALUES %s) AS v(plc_name, resource_name)
                                                                   JOIN plc p ON v.plc_name = p.plc_name
                                                                   JOIN resource r ON v.resource_name = r.resource_name)
                                )
                            """, [list(plc_resources)])
            else:
                cur.execute("DELETE FROM plc_resource")  # if nothing in YAML, clear all


if __name__ == "__main__":
    conn = psycopg2.connect(
        dbname="your_db",
        user="your_user",
        password="your_password",
        host="your_host"
    )
    sync_plcs_and_resources("plc.yaml", conn)
    conn.close()
