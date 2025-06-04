"""
File Reading and Data Processing Module

Information:
    This module provides functionality for reading data files and processing their contents.
    It includes classes for file reading and data transformation operations.

Date: 03/06/2025
Author: TOVY
"""

class FileReader:
    """Reads a file and splits content into lists of words."""

    def __init__(self, filename):
        """
        Information:
            Initialize the FileReader with a filename.

        Parameters:
            Input: filename - Path to the file to be read

        Date: 03/06/2025
        Author: TOVY
        """
        self.filename = filename

    def read_and_parse_file(self):
        """
        Information:
            Reads the file and splits content into word lists.
            Ignores empty lines in the file.

        Parameters:
            Output: List of lists, where each inner list contains words from a line

        Date: 03/06/2025
        Author: TOVY
        """
        with open(self.filename, "r") as f:
            lines = f.readlines()
        return [line.split() for line in lines if line.strip()]  # Ignore empty lines


class DataProcessor:
    """
    Information:
        Processes word lists by converting values.
        Provides static methods for data transformation operations.

    Date: 03/06/2025
    Author: TOVY
    """

    @staticmethod
    def convert_and_process_list(word_lists):
        """
        Information:
            Process each list of words, converting hexadecimal values.
            For each sublist, converts the first two characters of the first element to ASCII
            and the remaining characters to decimal, then combines them.

        Parameters:
            Input: word_lists - List of lists containing words to process
            Output: Generator yielding processed lists

        Date: 03/06/2025
        Author: TOVY
        """
        for sublist in word_lists:
            if sublist:
                first_part = sublist[0]
                ascii_hex, decimal_hex = first_part[:2], first_part[2:]
                try:
                    ascii_char = chr(int(ascii_hex, 16))
                    decimal_number = str(int(decimal_hex, 16)).zfill(5)
                    yield [ascii_char + decimal_number] + sublist[1:]
                except ValueError:
                    yield sublist


if __name__ == "__main__":
    # Instantiate FileReader and read the file
    file_reader = FileReader("../tests/for.dat")
    words_list = file_reader.read_and_parse_file()

    # Process the list using DataProcessor statically
    processed_list = list(DataProcessor.convert_and_process_list(words_list))

    for sublist in processed_list:
        print(sublist)