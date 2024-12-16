import os
import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

def get_taken_date(image_path):
    dates = []
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                if TAGS.get(tag) in ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']:
                    dates.append(datetime.datetime.strptime(value, '%Y:%m:%d %H:%M:%S'))
    except Exception as e:
        print(f"Error getting taken date from {image_path}: {e}")
    return dates

def get_media_creation_date(video_path):
    dates = []
    try:
        parser = createParser(video_path)
        metadata = extractMetadata(parser)
        if metadata:
            for date_tag in ["creation_date", "modification_date", "encoded_date", "tagged_date"]:
                if metadata.has(date_tag):
                    dates.append(metadata.get(date_tag))
    except Exception as e:
        print(f"Error getting media creation date from {video_path}: {e}")
    return dates

def get_file_date(file_path):
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
                dates.extend(get_file_date(old_file))
            elif file_extension in video_extensions:
                dates.extend(get_media_creation_date(old_file))
                dates.extend(get_file_date(old_file))
            else:
                continue

            oldest_date = get_oldest_date(dates)
            if oldest_date:
                new_name = oldest_date.strftime('%Y-%m-%d_%H-%M-%S') + file_extension

            if mode == "rename" and new_name:
                new_file = os.path.join(directory, new_name)
                os.rename(old_file, new_file)
                log_file.write(f"Renamed '{filename}' to '{new_name}'\n")
                print(f"Renamed '{filename}' to '{new_name}'")
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
