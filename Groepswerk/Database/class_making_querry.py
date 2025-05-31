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

    @staticmethod
    def convert_and_process_list(word_lists):
        """Process each list of words, yielding results."""
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