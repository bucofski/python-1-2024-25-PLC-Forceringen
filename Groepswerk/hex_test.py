
import pyodbc

# Path to your Access database file
db_file = r'C:/Users/SIDTOVY/OneDrive - ArcelorMittal/Desktop/controller_l.mdb'

# Connection string for Access (change Driver depending on your version)
conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    rf'DBQ={db_file};'
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Replace 'YourTableName' with the name of your table
cursor.execute("SELECT Name, MnemoK, [MnemoK'], Comment FROM NIET")
columns = [column[0] for column in cursor.description]

# Print column names
for col in columns:
    print(col)

conn.close()