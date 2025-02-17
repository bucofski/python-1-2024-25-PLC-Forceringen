
class FileReader:
    """Reads a file and splits content into lists of words."""

    def __init__(self, filename):
        self.filename = filename

    def read_and_parse_file(self):
        """Reads the file and splits content into word lists."""
        with open(self.filename, "r") as f:
            lines = f.readlines()
        return [line.split() for line in lines if line.strip()]  # Ignore empty lines


class DataProcessor:
    """Processes word lists by converting values."""

    def __init__(self, word_lists):
        self.word_lists = word_lists

    def convert_and_process_list(self):
        """Convert and process each list of words."""
        processed_list = []

        for sublist in self.word_lists:
            if sublist:
                # Convert the first value from hex to ascii + decimal
                first_part = sublist[0]
                ascii_hex, decimal_hex = first_part[:2], first_part[2:]
                try:
                    ascii_char = chr(int(ascii_hex, 16))
                    decimal_number = str(int(decimal_hex, 16)).zfill(5)
                    processed_list.append([ascii_char + decimal_number] + sublist[1:])
                except ValueError:
                    # Handle any conversion errors
                    processed_list.append(sublist)
        return processed_list


if __name__ == "__main__":
    # Instantiate FileReader and read the file
    file_reader = FileReader("for.dat")
    words_list = file_reader.read_and_parse_file()

    # Process the list using DataProcessor by creating an instance
    data_processor = DataProcessor(words_list)
    processed_list = data_processor.convert_and_process_list()

    for sublist in processed_list:
        print(sublist)
