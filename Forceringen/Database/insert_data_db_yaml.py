import os
import shutil
import asyncio
from Forceringen.util.unified_db_connection import DatabaseConnection
from Forceringen.util.config_manager import ConfigLoader
from pathlib import Path


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
        self.db_connection = DatabaseConnection(config_loader)
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

    def _cleanup_local_files(self, removed_plc_resources, removed_plcs):
        """
        Clean up local .dat files for removed PLCs and resources.
        
        Args:
            removed_plc_resources: Set of (plc_name, resource_name) tuples that were removed
            removed_plcs: Set of plc_names that were completely removed
        """
        base_local_dir = self.config_loader.get('local_base_dir', '')
        if not base_local_dir:
            print("Warning: local_base_dir not configured, skipping file cleanup")
            return

        # Clean up removed PLC-resource combinations
        for plc_name, resource_name in removed_plc_resources:
            # Use pathlib for cleaner path handling
            plc_dir = Path(base_local_dir) / plc_name
            if plc_dir.exists():
                # Look for files matching the pattern: {plc}_{resource}.dat
                dat_file = plc_dir / f"{plc_name}_{resource_name}.dat"
                if dat_file.exists():
                    try:
                        dat_file.unlink()  # pathlib's equivalent to os.remove()
                        print(f"Removed local file: {dat_file}")
                    except OSError as e:
                        print(f"Error removing file {dat_file}: {e}")
                        
        # Clean up completely removed PLCs (remove entire directory)
        for plc_name in removed_plcs:
            plc_dir = os.path.join(base_local_dir, plc_name)
            if os.path.exists(plc_dir):
                try:
                    shutil.rmtree(plc_dir)
                    print(f"Removed PLC directory: {plc_dir}")
                except OSError as e:
                    print(f"Error removing directory {plc_dir}: {e}")

    async def sync_async(self):
        """
        Synchronize PLCs and resources between YAML and database (asynchronous version).
        Uses the unified DatabaseConnection for database operations.
        """
        # Get async connection
        conn = await self.db_connection.get_connection(is_async=True)
        
        try:
            # Extract data from YAML
            self._extract_yaml_data()

            # Get existing PLCs and resources from database
            db_plcs = set()
            records = await conn.fetch_all("SELECT plc_name FROM plc")
            for record in records:
                db_plcs.add(record['plc_name'])

            db_resources = set()
            records = await conn.fetch_all("SELECT resource_name FROM resource")
            for record in records:
                db_resources.add(record['resource_name'])

            # Get existing PLC-resource pairs to identify removed combinations
            db_plc_resources = set()
            records = await conn.fetch_all("""
                SELECT p.plc_name, r.resource_name 
                FROM plc p
                JOIN resource_bit rb ON p.plc_id = rb.plc_id
                JOIN resource r ON rb.resource_id = r.resource_id
                GROUP BY p.plc_name, r.resource_name
            """)
            for record in records:
                db_plc_resources.add((record['plc_name'], record['resource_name']))

            # Find removed PLC-resource combinations and completely removed PLCs
            removed_plc_resources = db_plc_resources - self.plc_resources
            removed_plcs = db_plcs - self.yaml_plcs

            # Clean up local files BEFORE database cleanup
            self._cleanup_local_files(removed_plc_resources, removed_plcs)

            # Database cleanup (existing code)
            for plc_name, resource_name in removed_plc_resources:
                print(f"Removing PLC-resource combination: {plc_name}-{resource_name}")
                await conn.execute(
                    "EXEC delete_plc_resource_bits :plc_name, :resource_name", 
                    {"plc_name": plc_name, "resource_name": resource_name}
                )

            # Delete PLCs that are in DB but not in YAML
            for plc_name in removed_plcs:
                print(f"Removing PLC: {plc_name}")
                await conn.execute("EXEC delete_plc_all_bits :plc_name", {"plc_name": plc_name})
                await conn.execute("DELETE FROM plc WHERE plc_name = :plc_name", {"plc_name": plc_name})

            # Delete resources that are in DB but not in YAML (optional)
            for resource_name in db_resources - self.yaml_resources:
                await conn.execute("DELETE FROM resource WHERE resource_name = :resource_name", {"resource_name": resource_name})

            # REMOVED: Manual INSERT statements for PLCs and resources
            # Let the upsert_plc_bits procedure handle creating them when needed

            print(f"Sync completed. YAML has {len(self.yaml_plcs)} PLCs and {len(self.yaml_resources)} resources")

        finally:
            await conn.disconnect()

    # def sync(self):
    #     """
    #     Synchronous version of sync for backwards compatibility.
    #     Uses the unified DatabaseConnection for synchronous operations.
    #     """
    #     # Get sync connection
    #     conn = self.db_connection.get_connection(is_async=False)
    #     cursor = conn.cursor()
    #
    #     try:
    #         # Extract data from YAML
    #         self._extract_yaml_data()
    #
    #         # Get existing PLCs and resources from database
    #         db_plcs = set()
    #         cursor.execute("SELECT plc_name FROM plc")
    #         records = cursor.fetchall()
    #         for record in records:
    #             db_plcs.add(record[0])  # pytds returns tuples
    #
    #         db_resources = set()
    #         cursor.execute("SELECT resource_name FROM resource")
    #         records = cursor.fetchall()
    #         for record in records:
    #             db_resources.add(record[0])
    #
    #         # Get existing PLC-resource pairs
    #         db_plc_resources = set()
    #         cursor.execute("""
    #             SELECT p.plc_name, r.resource_name
    #             FROM plc p
    #             JOIN resource_bit rb ON p.plc_id = rb.plc_id
    #             JOIN resource r ON rb.resource_id = r.resource_id
    #             GROUP BY p.plc_name, r.resource_name
    #         """)
    #         records = cursor.fetchall()
    #         for record in records:
    #             db_plc_resources.add((record[0], record[1]))
    #
    #         # Find removed PLC-resource combinations and completely removed PLCs
    #         removed_plc_resources = db_plc_resources - self.plc_resources
    #         removed_plcs = db_plcs - self.yaml_plcs
    #
    #         # Clean up local files BEFORE database cleanup
    #         self._cleanup_local_files(removed_plc_resources, removed_plcs)
    #
    #         # Database cleanup (existing code)
    #         for plc_name, resource_name in removed_plc_resources:
    #             print(f"Removing PLC-resource combination: {plc_name}-{resource_name}")
    #             cursor.execute("EXEC delete_plc_resource_bits ?, ?", (plc_name, resource_name))
    #
    #         # Delete PLCs that are in DB but not in YAML
    #         for plc_name in removed_plcs:
    #             print(f"Removing PLC: {plc_name}")
    #             cursor.execute("EXEC delete_plc_all_bits ?", (plc_name,))
    #             cursor.execute("DELETE FROM plc WHERE plc_name = ?", (plc_name,))
    #
    #         # Delete resources that are in DB but not in YAML
    #         for resource_name in db_resources - self.yaml_resources:
    #             cursor.execute("DELETE FROM resource WHERE resource_name = ?", (resource_name,))
    #
    #         # Insert new PLCs
    #         for plc in self.yaml_plcs:
    #             cursor.execute("""
    #                 IF NOT EXISTS (SELECT 1 FROM plc WHERE plc_name = ?)
    #                 INSERT INTO plc (plc_name) VALUES (?)
    #             """, (plc, plc))
    #
    #         # Insert new Resources
    #         for resource in self.yaml_resources:
    #             cursor.execute("""
    #                 IF NOT EXISTS (SELECT 1 FROM resource WHERE resource_name = ?)
    #                 INSERT INTO resource (resource_name) VALUES (?)
    #             """, (resource, resource))
    #
    #         # Commit the transaction
    #         conn.commit()
    #
    #     except Exception as e:
    #         conn.rollback()
    #         raise e
    #     finally:
    #         cursor.close()
    #         conn.close()
    #

if __name__ == "__main__":
    async def main():
        yaml_path = "../config/plc.yaml"
        config_loader = ConfigLoader(yaml_path)

        # Create and use the sync class
        plc_sync = PLCResourceSync(config_loader)
        await plc_sync.sync_async()  # For asynchronous operation


    # Run the async main function
    asyncio.run(main())