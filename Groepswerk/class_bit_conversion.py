import struct
from datetime import datetime
from class_making_querry import DataProcessor, FileReader
from class_database import DatabaseSearcher


class BitConversion:
    def __init__(self, data_list):
        """Initialize with a list of dictionaries from the database search."""
        self.data_list = data_list

    def convert_variable_list(self):
        """Convert and process values based on type. Modifies self.data_list in-place."""
        for sublist in self.data_list:
            value = sublist.get("Value", [])
            type_ = sublist.get("VAR_Type")

            try:
                if type_ == 'REAL' and value:
                    int_value = int(value[0], 16)
                    float_value = struct.unpack('!f', struct.pack('!I', int_value))[0]
                    sublist["Value"] = str(float_value)

                elif type_ == 'LINT' and value:
                    sublist["Value"] = int(value[0], 16)

                elif type_ == 'DOUBLE' and value:
                    hex_combined = ''.join(value[::-1])
                    int_value = int(hex_combined, 16)
                    double_precision_float = struct.unpack('>d', struct.pack('>Q', int_value))[0]
                    sublist["Value"] = str(double_precision_float)

                elif type_ == 'BOOL':
                    int_value = int(value[0], 16)
                    sublist["Value"] = bool(int_value)

            except (ValueError, IndexError, struct.error):
                sublist["Value"] = f"Invalid {type_}"

        return self.data_list


if __name__ == "__main__":
    start = datetime.now()

    # Read and process the input file only once
    words_list = FileReader("BTEST_NIET.dat").read_and_parse_file()
    processed_words = list(DataProcessor.convert_and_process_list(words_list))

    # Initialize database searcher and perform search within context manager
    db_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"
    custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"
    with DatabaseSearcher(db_path) as searcher:
        results = searcher.search(processed_words, query_template=custom_query)

    # Convert bits
    bit_converter = BitConversion(results)
    common_elements = bit_converter.convert_variable_list()

    end = datetime.now()
    print(f"Time taken: {(end - start).total_seconds()} seconds")
    for sublist in common_elements:
        print(sublist)
