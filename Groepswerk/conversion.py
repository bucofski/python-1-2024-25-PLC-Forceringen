import struct


def read_and_split_file(filename):
    """Read the file and split content into lists of words."""
    with open(filename, "r") as f:
        lines = f.readlines()
    return [line.split() for line in lines if line.strip()]  # Split non-empty lines

def convert_and_process_list(word_lists):
    """Convert and process word lists."""
    processed_list = []

    for sublist in word_lists:
        if sublist:
            # convert the first value from hex to ascii + decimal example:
            # 57008441 (57 hex ascii = W) and 008441 hex is 33857 together = W33857
            first_part = sublist[0]
            ascii_hex, decimal_hex = first_part[:2], first_part[2:]

            ascii_char = chr(int(ascii_hex, 16))
            decimal_number = str(int(decimal_hex, 16)).zfill(5)

            # convert the second value from IEEE 754 single-precision format to floating point
            if len(sublist[1]) > 4 and sublist[1] not in {"0", "1"}:
                int_value = int(sublist[1], 16)
                float_value = struct.unpack('!f', struct.pack('!I', int_value))[0]
                sublist[1] = str(float_value)
            # if value isn't single-precision but hex
            elif len(sublist[1]) < 8 and sublist[1] not in {"0", "1"}:
                sublist[1] = int(sublist[1], 16)
            # put it all together in one list
            processed_list.append([ascii_char + decimal_number] + sublist[1:])

    return processed_list


if __name__ == "__main__":
    words_list = read_and_split_file("for.dat")
    converted_list = convert_and_process_list(words_list)

    for sublist in converted_list:
        print(sublist)

    # assert convert_and_process_list(["57008441", "1", "0"]) == ['W33857', '1', '0']
    # assert convert_and_process_list(["57008450", "1", "0"]) == ['W33872', '1', '0']
    # assert convert_and_process_list(["57007c57", "1", "0"]) == ['W31831', '1', '0']
    # assert convert_and_process_list(["57005a66", "1", "0"]) == ['W23142', '1', '0']
    # assert convert_and_process_list(["57003245", "47f12010", "0"]) == ['W33857', '123456.125', '0']
    # assert convert_and_process_list(["52000700", "47f12000", "0"]) == ['R01792', '123456.0', '0']