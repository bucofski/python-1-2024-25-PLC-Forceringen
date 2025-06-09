import struct
from datetime import datetime
from Forceringen.PLC.convert_dat_file import DataProcessor, FileReader
from Forceringen.PLC.Search_Access import DatabaseSearcher


class BitConversion:
    """
    Information:
        A class for converting hexadecimal data into appropriate Python data types based on
        their specified variable types from database query results.

    Parameters:
        Input: List of dictionaries containing variable data with 'Value' and 'VAR_Type' keys

    Date: 03/06/2025
    Author: TOVY
    """
    def __init__(self, data_list):
        """
        Information:
            Initialize the BitConversion class with data to be converted.

        Parameters:
            Input: data_list - A list of dictionaries from the database search

        Date: 03/06/2025
        Author: TOVY
        """
        self.data_list = data_list

    def convert_variable_list(self):
        """
        Information:
            Convert and process values based on their respective types.
            Supported conversions:
            - REAL: Converts hex to single-precision float
            - LINT: Converts hex to integer
            - DOUBLE: Converts hex to double-precision float
            - BOOL: Converts hex to boolean
            If conversion fails, the Value will be set to "Invalid {type_}"

        Parameters:
            Output: The modified list with converted values

        Date: 03/06/2025
        Author: TOVY
        """
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
    """
    Information:
        Main execution block that demonstrates the usage of the BitConversion class.
        Process flow:
        1. Reads and parses data from a file
        2. Processes the data
        3. Searches a database for the processed data
        4. Converts the results using BitConversion
        5. Prints the time taken and the converted results
    """
    start = datetime.now()

    # Read and process the input file only once
    words_list = FileReader("../tests/BTEST_NIET.dat").read_and_parse_file()
    processed_words = list(DataProcessor.convert_and_process_list(words_list))

    # Initialize database searcher and perform search within context manager
    db_path = r"C:/Users/tom_v/OneDrive/Documenten/database/project/controller_l.mdb"
    custom_query = "SELECT *, SecondComment FROM NIET WHERE Name IN ({placeholders})"
    with DatabaseSearcher(db_path) as searcher:
        results = searcher.search(processed_words, query_template=custom_query, department_name="bt2", plc="BTEST",
                                  resource="NIET")

    # Convert bits
    bit_converter = BitConversion(results)
    common_elements = bit_converter.convert_variable_list()

    end = datetime.now()
    print(f"Time taken: {(end - start).total_seconds()} seconds")
    for sublist in common_elements:
        print(sublist)
