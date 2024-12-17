import os

def find_and_delete_duplicates(directory, mode):
    log_file = open("jpeg_delete_log.txt", "w")

    for root, _, files in os.walk(directory):
        jpg_files = {os.path.splitext(f)[0]: f for f in files if f.lower().endswith('.jpg')}
        jpeg_files = {os.path.splitext(f)[0]: f for f in files if f.lower().endswith('.jpeg')}

        for name in jpeg_files:
            if name in jpg_files:
                jpeg_file_path = os.path.join(root, jpeg_files[name])
                jpg_file_path = os.path.join(root, jpg_files[name])
                if mode == "delete":
                    try:
                        os.remove(jpeg_file_path)
                        log_file.write(f"Deleted: {jpeg_file_path}\n")
                        print(f"Deleted: {jpeg_file_path}")
                    except Exception as e:
                        log_file.write(f"Error deleting {jpeg_file_path}: {e}\n")
                        print(f"Error deleting {jpeg_file_path}: {e}")
                elif mode == "validate":
                    log_file.write(f"Would delete: {jpeg_file_path}\n")
                    print(f"Would delete: {jpeg_file_path}")

    log_file.close()

if __name__ == "__main__":
    directory = input("Enter the directory path: ")
    mode = input("Enter the mode (delete/validate): ").strip().lower()
    if mode not in ["delete", "validate"]:
        print("Invalid mode. Please enter 'delete' or 'validate'.")
    else:
        find_and_delete_duplicates(directory, mode)