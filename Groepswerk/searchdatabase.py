import pyodbc
import getforcebit
from getforcebit import convert_and_process_list, read_and_parse_file
# Voorbeeldlijst
def search_database(item_list):
    # Plat de lijst af
    flattened_list = [item[0] for item in item_list]

    # Pad naar de Access-database
    mdb_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"

    # ODBC-verbinding
    connection_string = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={mdb_path};"
    )

    try:
        # Verbind met de database
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        if flattened_list:  # Controleer of de lijst niet leeg is
            # Genereer placeholders
            placeholders = ", ".join("?" for _ in flattened_list)
            query = f"SELECT * FROM NIET WHERE Name IN ({placeholders})"

            # Voer de query uit
            cursor.execute(query, flattened_list)
            results = cursor.fetchall()

            # Verwerk de resultaten
            return results
        else:
            print("De lijst met te zoeken items is leeg. Beëindig query.")

    except pyodbc.Error as e:
        print(f"Er is een fout opgetreden: {e}")

    finally:
        # Sluit de verbinding
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    words_list = read_and_parse_file("for.dat")
    item_list = convert_and_process_list(words_list)
    results = search_database(item_list)
    for row in results:
        print(row)