import os
import re

def export_file_info(directory):
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")

    year = input("Enter the year for files that do not contain a year: ").strip()
    if not re.fullmatch(r'(19|20)\d{2}', year):
        raise ValueError("Year must be four digits between 1900 and 2099.")

    year_pattern = re.compile(rf'(?<!\d){re.escape(year)}(?!\d)')

    with open("file_info.txt", "w", encoding="utf-8") as file_info:
        for root, _, files in os.walk(directory):
            for filename in files:
                if not year_pattern.search(filename):
                    file_info.write(f"File Name: {filename}, Path: {os.path.join(root, filename)}\n")

if __name__ == "__main__":
    directory = input("Enter the directory path: ")
    if not os.path.isdir(directory):
        print(f"Directory does not exist: {directory}")
    else:
        try:
            export_file_info(directory)
        except ValueError as e:
            print(e)