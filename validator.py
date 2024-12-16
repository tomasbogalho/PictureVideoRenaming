import os
import re

def export_file_info(directory):
    home_directory = os.path.expanduser("~")
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    
    year = input("Enter the year for files that do not contain a year: ")
    
    with open("file_info.txt", "w") as file_info:
        for root, _, files in os.walk(directory):
            for filename in files:
                if year not in filename:
                    file_info.write(f"File Name: {filename}, Path: {os.path.join(root, filename)}\n")

if __name__ == "__main__":
    directory = input("Enter the directory path: ")
    export_file_info(directory)