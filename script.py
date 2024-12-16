import os
import datetime
import time
import shutil
from PIL import Image
from PIL.ExifTags import TAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

def get_taken_date(image_path):
    dates = []
    try:
        with Image.open(image_path) as image:
            exif_data = image._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    if TAGS.get(tag) in ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']:
                        dates.append(datetime.datetime.strptime(value, '%Y:%m:%d %H:%M:%S'))
    except Exception as e:
        print(f"Error getting taken date from {image_path}: {e}")
    return dates

def get_media_creation_date(video_path):
    try:
        parser = createParser(video_path)
        if not parser:
            print(f"Unable to parse file {video_path}")
            return None
        with parser:
            metadata = extractMetadata(parser)
            if metadata and metadata.has("creation_date"):
                return metadata.get("creation_date")
    except Exception as e:
        print(f"Error getting media creation date from {video_path}: {e}")
    return None

def get_file_dates(file_path):
    creation_date = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
    modification_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
    return [creation_date, modification_date]

def get_oldest_date(dates):
    if dates:
        return min(dates)
    return None

def rename_files(directory, mode):
    picture_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv']
    files = os.listdir(directory)
    log_file = open("rename_log.txt", "w")

    for filename in files:
        file_extension = os.path.splitext(filename)[1].lower()
        old_file = os.path.join(directory, filename)
        new_name = None

        try:
            dates = []
            if file_extension in picture_extensions:
                dates.extend(get_taken_date(old_file))
                dates.extend(get_file_dates(old_file))
            elif file_extension in video_extensions:
                media_creation_date = get_media_creation_date(old_file)
                if media_creation_date:
                    dates.append(media_creation_date)
                dates.extend(get_file_dates(old_file))
            else:
                continue

            oldest_date = get_oldest_date(dates)
            if oldest_date:
                new_name = oldest_date.strftime('%Y-%m-%d_%H-%M-%S') + file_extension

            if mode == "rename" and new_name:
                new_file = os.path.join(directory, new_name)
                counter = 1
                while os.path.exists(new_file):
                    new_file = os.path.join(directory, f"{oldest_date.strftime('%Y-%m-%d_%H-%M-%S')}_{counter}{file_extension}")
                    counter += 1

                for _ in range(5):  # Retry up to 5 times
                    try:
                        shutil.move(old_file, new_file)
                        log_file.write(f"Renamed '{filename}' to '{new_name}'\n")
                        print(f"Renamed '{filename}' to '{new_name}'")
                        break
                    except PermissionError as e:
                        print(f"Error renaming '{filename}': {e}. Retrying...")
                        time.sleep(1)  # Wait for 1 second before retrying
            elif mode == "validate" and new_name:
                log_file.write(f"'{filename}' would be renamed to '{new_name}'\n")
                print(f"'{filename}' would be renamed to '{new_name}'")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    log_file.close()

if __name__ == "__main__":
    directory = input("Enter the directory path: ")
    mode = input("Enter the mode (rename/validate): ").strip().lower()
    if mode not in ["rename", "validate"]:
        print("Invalid mode. Please enter 'rename' or 'validate'.")
    else:
        rename_files(directory, mode)