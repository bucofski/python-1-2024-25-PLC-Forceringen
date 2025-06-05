import psycopg2
from Groepswerk.util.class_config_loader import ConfigLoader


class PLCResourceSync:
    """
    Class for synchronizing PLCs and resources between YAML configuration
    and database. Handles both synchronous and asynchronous operations.
    """
    
    def __init__(self, config_loader):
        """
        Initialize with a ConfigLoader instance.
        
        Args:
            config_loader: Instance of ConfigLoader containing configuration data
        """
        self.config_loader = config_loader
        self.yaml_plcs = set()
        self.yaml_resources = set()
        self.plc_resources = set()
        
    def _extract_yaml_data(self):
        """
        Extract PLCs and resources data from YAML configuration.
        """
        self.yaml_plcs.clear()
        self.yaml_resources.clear()
        self.plc_resources.clear()
        
        for host in self.config_loader.get_sftp_hosts():
            plc = host.get('hostname')
            resources = host.get('resources', [])
            self.yaml_plcs.add(plc)
            for resource in resources:
                self.yaml_resources.add(resource)
                self.plc_resources.add((plc, resource))
    
    def sync(self, conn):
        """
        Synchronize PLCs and resources between YAML and database (synchronous version).

        Args:
            conn: PostgreSQL database connection
        """
        # Extract data from YAML
        self._extract_yaml_data()

        with conn:
            with conn.cursor() as cur:
                # Get existing PLCs and resources from database
                cur.execute("SELECT plc_name FROM plc")
                db_plcs = {row[0] for row in cur.fetchall()}

                cur.execute("SELECT resource_name FROM resource")
                db_resources = {row[0] for row in cur.fetchall()}

                # Get existing PLC-resource pairs to identify removed combinations
                cur.execute("""
                    SELECT p.plc_name, r.resource_name
                    FROM plc p
                    JOIN resource_bit rb ON p.plc_id = rb.plc_id
                    JOIN resource r ON rb.resource_id = r.resource_id
                    GROUP BY p.plc_name, r.resource_name
                """)
                db_plc_resources = {(row[0], row[1]) for row in cur.fetchall()}

                # Find removed PLC-resource combinations
                removed_plc_resources = db_plc_resources - self.plc_resources
                for plc_name, resource_name in removed_plc_resources:
                    print(f"Removing PLC-resource combination: {plc_name}-{resource_name}")
                    cur.execute("SELECT * FROM delete_plc_resource_bits(%s, %s)", (plc_name, resource_name))

                # Delete PLCs that are in DB but not in YAML
                plcs_to_delete = db_plcs - self.yaml_plcs
                for plc_name in plcs_to_delete:
                    print(f"Removing PLC: {plc_name}")
                    cur.execute("SELECT * FROM delete_plc_all_bits(%s)", (plc_name,))
                    cur.execute("DELETE FROM plc WHERE plc_name = %s", (plc_name,))

                # Delete resources that are in DB but not in YAML (optional)
                resources_to_delete = db_resources - self.yaml_resources
                for resource_name in resources_to_delete:
                    cur.execute("DELETE FROM resource WHERE resource_name = %s", (resource_name,))

                # Insert new PLCs
                for plc in self.yaml_plcs:
                    cur.execute("""
                                INSERT INTO plc (plc_name)
                                VALUES (%s) ON CONFLICT (plc_name) DO NOTHING
                                """, (plc,))

                # Insert new Resources
                for resource in self.yaml_resources:
                    cur.execute("""
                                INSERT INTO resource (resource_name)
                                VALUES (%s) ON CONFLICT (resource_name) DO NOTHING
                                """, (resource,))

    async def sync_async(self, conn):
        """
        Synchronize PLCs and resources between YAML and database (asynchronous version).

        Args:
            conn: asyncpg database connection
        """
        # Extract data from YAML
        self._extract_yaml_data()

        # Get existing PLCs and resources from database
        db_plcs = set()
        records = await conn.fetch("SELECT plc_name FROM plc")
        for record in records:
            db_plcs.add(record['plc_name'])

        db_resources = set()
        records = await conn.fetch("SELECT resource_name FROM resource")
        for record in records:
            db_resources.add(record['resource_name'])

        # Get existing PLC-resource pairs to identify removed combinations
        db_plc_resources = set()
        records = await conn.fetch("""
            SELECT p.plc_name, r.resource_name 
            FROM plc p
            JOIN resource_bit rb ON p.plc_id = rb.plc_id
            JOIN resource r ON rb.resource_id = r.resource_id
            GROUP BY p.plc_name, r.resource_name
        """)
        for record in records:
            db_plc_resources.add((record['plc_name'], record['resource_name']))

        # Find removed PLC-resource combinations
        removed_plc_resources = db_plc_resources - self.plc_resources
        for plc_name, resource_name in removed_plc_resources:
            print(f"Removing PLC-resource combination: {plc_name}-{resource_name}")
            await conn.fetch("SELECT * FROM delete_plc_resource_bits($1, $2)", plc_name, resource_name)

        # Delete PLCs that are in DB but not in YAML
        for plc_name in db_plcs - self.yaml_plcs:
            print(f"Removing PLC: {plc_name}")
            await conn.fetch("SELECT * FROM delete_plc_all_bits($1)", plc_name)
            await conn.execute("DELETE FROM plc WHERE plc_name = $1", plc_name)

        # Delete resources that are in DB but not in YAML (optional)
        for resource_name in db_resources - self.yaml_resources:
            await conn.execute("DELETE FROM resource WHERE resource_name = $1", resource_name)

        # Insert new PLCs
        for plc in self.yaml_plcs:
            await conn.execute("""
                            INSERT INTO plc (plc_name)
                            VALUES ($1) ON CONFLICT (plc_name) DO NOTHING
                            """, plc)

        # Insert new Resources
        for resource in self.yaml_resources:
            await conn.execute("""
                            INSERT INTO resource (resource_name)
                            VALUES ($1) ON CONFLICT (resource_name) DO NOTHING
                            """, resource)

        # Build lookup maps for IDs if needed for other operations
        plc_lookup = {}
        records = await conn.fetch("SELECT plc_id, plc_name FROM plc")
        for record in records:
            plc_lookup[record['plc_name']] = record['plc_id']

        resource_lookup = {}
        records = await conn.fetch("SELECT resource_id, resource_name FROM resource")
        for record in records:
            resource_lookup[record['resource_name']] = record['resource_id']


if __name__ == "__main__":
    yaml_path = "../config/plc.yaml"
    config_loader = ConfigLoader(yaml_path)
    pg_info = config_loader.get_database_info()
    conn = psycopg2.connect(**pg_info)
    
    # Create and use the sync class
    plc_sync = PLCResourceSync(config_loader)
    plc_sync.sync(conn)
    conn.close()