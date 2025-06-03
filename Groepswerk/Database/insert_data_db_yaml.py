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
        Information:
            Synchronizes PLCs and resources between YAML and database using a synchronous connection.
            This includes:
            - Extracting data from YAML configuration
            - Identifying differences between YAML and database
            - Deleting PLCs and resources that exist in the database but not in YAML
            - Adding PLCs and resources that exist in YAML but not in the database

        Parameters:
            Input: conn - PostgreSQL database connection (psycopg2)

        Date: 03/06/2025
        Author: TOVY
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

                # Delete PLCs that are in DB but not in YAML
                plcs_to_delete = db_plcs - self.yaml_plcs
                for plc_name in plcs_to_delete:
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

                # # Build lookup maps for IDs if needed for other operations
                # cur.execute("SELECT plc_id, plc_name FROM plc")
                # plc_lookup = {name: plc_id for plc_id, name in cur.fetchall()}
                # cur.execute("SELECT resource_id, resource_name FROM resource")
                # resource_lookup = {name: res_id for res_id, name in cur.fetchall()}

                # # For each PLC-resource pair, we could create placeholder entries in resource_bit
                # for plc, resource in self.plc_resources:
                #     cur.execute("""
                #                 SELECT COUNT(*)
                #                 FROM resource_bit
                #                 WHERE plc_id = %s
                #                   AND resource_id = %s
                #                 """, (plc_lookup[plc], resource_lookup[resource]))
                #     count = cur.fetchone()[0]
                #     if count == 0:
                #         cur.execute("""
                #                     INSERT INTO resource_bit (plc_id, resource_id)
                #                     VALUES (%s, %s) ON CONFLICT DO NOTHING
                #                     """, (plc_lookup[plc], resource_lookup[resource]))
    
    async def sync_async(self, conn):
        """
        Information:
            Synchronizes PLCs and resources between YAML and database using an asynchronous connection.
            This includes:
            - Extracting data from YAML configuration
            - Identifying differences between YAML and database
            - Deleting PLCs and resources that exist in the database but not in YAML
            - Adding PLCs and resources that exist in YAML but not in the database
            - Building lookup maps for PLC and resource IDs

        Parameters:
            Input: conn - asyncpg database connection

        Date: 03/06/2025
        Author: TOVY
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

        # Delete PLCs that are in DB but not in YAML
        for plc_name in db_plcs - self.yaml_plcs:
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

        # # For each PLC-resource pair, we could create placeholder entries in resource_bit
        # for plc, resource in self.plc_resources:
        #     count = await conn.fetchval("""
        #                     SELECT COUNT(*)
        #                     FROM resource_bit
        #                     WHERE plc_id = $1
        #                       AND resource_id = $2
        #                     """, plc_lookup[plc], resource_lookup[resource])
        #
        #     if count == 0:
        #         await conn.execute("""
        #                            INSERT INTO resource_bit (plc_id, resource_id)
        #                            VALUES ($1, $2) ON CONFLICT DO NOTHING
        #                            """, plc_lookup[plc], resource_lookup[resource])


if __name__ == "__main__":
    yaml_path = "../config/plc.yaml"
    config_loader = ConfigLoader(yaml_path)
    pg_info = config_loader.get_database_info()
    conn = psycopg2.connect(**pg_info)
    
    # Create and use the sync class
    plc_sync = PLCResourceSync(config_loader)
    plc_sync.sync(conn)
    conn.close()