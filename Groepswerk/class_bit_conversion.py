import struct
from datetime import datetime
from class_making_querry import DataProcessor, FileReader
from class_database import DatabaseSearcher

class BitConversion:
    def __init__(self, data_list):
        """Initialize with a list of dictionaries from the database search."""
        self.data_list = data_list

    def convert_variable_list(self, DataProcessor, words_list):
        """Convert and process values based on type."""

        processed_list = DataProcessor(words_list).convert_and_process_list()

        for sublist in self.data_list:
            value = sublist.get("Value", [])
            type_ = sublist.get("Type")

            if type_ == 'REAL':
                try:
                    int_value = int(value[0], 16)
                    float_value = struct.unpack('!f', struct.pack('!I', int_value))[0]
                    sublist["Value"] = str(float_value)
                except (ValueError, IndexError):
                    sublist["Value"] = "Invalid REAL"

            elif type_ == 'LINT':
                try:
                    sublist["Value"] = int(value[0], 16)
                except (ValueError, IndexError):
                    sublist["Value"] = "Invalid LINT"

            elif type_ == 'DOUBLE':
                try:
                    # Combine them into a single 64-bit hex string (big-endian order)
                    hex_combined = ''.join(value[::-1])

                    # Convert to integer
                    int_value = int(hex_combined, 16)

                    # Interpret as IEEE 754 double-precision float
                    double_precision_float = struct.unpack('>d', struct.pack('>Q', int_value))[0]

                    # If you're expecting a double value as a return, you can optionally update sublist["Value"];
                    # otherwise, you might want to continue processing other sublists.
                    sublist["Value"] = str(double_precision_float)

                except (ValueError, IndexError) as e:
                    sublist["Value"] = "Invalid DOUBLE"

            processed_list.append(sublist)

        return processed_list

if __name__ == "__main__":
    start = datetime.now()
    # Instantiate FileReader and read the file
    file_reader = FileReader("for.dat")
    words_list = file_reader.read_and_parse_file()

    # # Process the list using DataProcessor by creating an instance
    # processed_list = DataProcessor(words_list).convert_and_process_list()
    # #processed_list = data_processor.convert_and_process_list()

    # Initialize database searcher
    db_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"
    searcher = DatabaseSearcher(db_path)

    # Perform database search
    custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"

    # Perform search
    results = searcher.search(DataProcessor(words_list).convert_and_process_list(), query_template=custom_query)

    # Process results through BitConversion
    bit_converter = BitConversion(results)
    common_elements = bit_converter.convert_variable_list(DataProcessor, words_list)
  # FIXED: Call method on instance

    end = datetime.now()
    print(f"Time taken: {(end - start).total_seconds()} seconds")

    # Print results
    for sublist in common_elements:
        print(sublist)
