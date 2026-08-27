import os
import hashlib

def files_are_identical(first_path, second_path):
    if os.path.getsize(first_path) != os.path.getsize(second_path):
        return False

    first_hash = hashlib.sha256()
    second_hash = hashlib.sha256()
    with open(first_path, "rb") as first_file, open(second_path, "rb") as second_file:
        while True:
            first_chunk = first_file.read(1024 * 1024)
            second_chunk = second_file.read(1024 * 1024)
            if not first_chunk and not second_chunk:
                break
            first_hash.update(first_chunk)
            second_hash.update(second_chunk)
    return first_hash.digest() == second_hash.digest()

def find_and_delete_duplicates(directory, mode):
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")
    if mode not in ["delete", "validate"]:
        raise ValueError("Mode must be 'delete' or 'validate'.")

    with open("jpeg_delete_log.txt", "w", encoding="utf-8") as log_file:
        for root, _, files in os.walk(directory):
            jpg_files = {os.path.splitext(f)[0].lower(): f for f in files if f.lower().endswith('.jpg')}
            jpeg_files = {os.path.splitext(f)[0].lower(): f for f in files if f.lower().endswith('.jpeg')}

            for name in jpeg_files:
                if name not in jpg_files:
                    continue

                jpeg_file_path = os.path.join(root, jpeg_files[name])
                jpg_file_path = os.path.join(root, jpg_files[name])
                try:
                    if not files_are_identical(jpg_file_path, jpeg_file_path):
                        message = f"Skipped different files: {jpg_file_path} and {jpeg_file_path}"
                        log_file.write(message + "\n")
                        print(message)
                    elif mode == "delete":
                        os.remove(jpeg_file_path)
                        log_file.write(f"Deleted: {jpeg_file_path}\n")
                        print(f"Deleted: {jpeg_file_path}")
                    else:
                        log_file.write(f"Would delete identical file: {jpeg_file_path}\n")
                        print(f"Would delete identical file: {jpeg_file_path}")
                except OSError as e:
                    log_file.write(f"Error checking or deleting {jpeg_file_path}: {e}\n")
                    print(f"Error checking or deleting {jpeg_file_path}: {e}")

if __name__ == "__main__":
    directory = input("Enter the directory path: ")
    mode = input("Enter the mode (delete/validate): ").strip().lower()
    if mode not in ["delete", "validate"]:
        print("Invalid mode. Please enter 'delete' or 'validate'.")
    elif not os.path.isdir(directory):
        print(f"Directory does not exist: {directory}")
    else:
        find_and_delete_duplicates(directory, mode)