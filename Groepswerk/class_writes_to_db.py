import ast
import psycopg2

class DatabaseManager:
    def __init__(self, config):
        self.conn = psycopg2.connect(**config)
        self.cur = self.conn.cursor()

    def close(self):
        self.cur.close()
        self.conn.close()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def insert_resource_bit(self, resource_name, bit_number, kks, comment, second_comment, value):
        self.cur.execute(
            "SELECT insert_resource_bit(%s, %s, %s, %s, %s, %s);",
            (resource_name, bit_number, kks, comment, second_comment, value)
        )


DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'PLC_Forceringen',
    'user': 'postgres',
    'password': '123'
}
RESOURCE_DEFAULT = 'NIET'

def main():
    db = DatabaseManager(DB_CONFIG)

    # Step 1: Reset all force_active flags
    try:
        db.cur.execute("UPDATE resource_bit SET force_active = FALSE;")
        db.commit()
    except Exception as reset_err:
        print(f"❌ Error resetting force_active flags: {reset_err}")
        db.rollback()

    # Step 2: Read and import bit data
    try:
        with open('test.txt', 'r') as text_file:
            for line in text_file:
                try:
                    data = ast.literal_eval(line.strip())

                    bit_number = data['name_id']
                    kks = str(data['KKS'])
                    comment = str(data.get('Comment', 'None'))
                    second_comment = str(data.get('Second_comment', 'None'))
                    value = str(data.get('Value', 'NULL'))
                    resource_name = data.get('resource') or RESOURCE_DEFAULT

                    db.insert_resource_bit(resource_name, bit_number, kks, comment, second_comment, value)
                except Exception as bit_err:
                    print(f"❌ Error inserting bit {data.get('name_id', '?')}: {bit_err}")
                    db.rollback()
                else:
                    db.commit()
        print("✅ Bit data imported successfully.")
    except Exception as e:
        print(f"❌ Error reading bit file: {e}")

    db.close()

if __name__ == "__main__":
    main()
