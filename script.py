import os
import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

def get_taken_date(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                if TAGS.get(tag) == 'DateTimeOriginal':
                    return datetime.datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        print(f"Error getting taken date from {image_path}: {e}")
    return None

def get_media_creation_date(video_path):
    try:
        parser = createParser(video_path)
        metadata = extractMetadata(parser)
        if metadata and metadata.has("creation_date"):
            return metadata.get("creation_date").value
    except Exception as e:
        print(f"Error getting media creation date from {video_path}: {e}")
    return None

def get_file_date(file_path):
    creation_date = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
    modification_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
    return min(creation_date, modification_date)

def rename_files(directory):
    picture_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv']
    files = os.listdir(directory)
    log_file = open("rename_log.txt", "w")

    for filename in files:
        file_extension = os.path.splitext(filename)[1].lower()
        old_file = os.path.join(directory, filename)
        new_name = None

        try:
            if file_extension in picture_extensions:
                taken_date = get_taken_date(old_file)
                if not taken_date:
                    taken_date = get_file_date(old_file)
                new_name = taken_date.strftime('%Y-%m-%d_%H-%M-%S') + file_extension
            elif file_extension in video_extensions:
                creation_date = get_media_creation_date(old_file)
                if not creation_date:
                    creation_date = get_file_date(old_file)
                new_name = creation_date.strftime('%Y-%m-%d_%H-%M-%S') + file_extension
            else:
                continue

            new_file = os.path.join(directory, new_name)
            os.rename(old_file, new_file)
            log_file.write(f"Renamed '{filename}' to '{new_name}'\n")
            print(f"Renamed '{filename}' to '{new_name}'")
        except Exception as e:
            print(f"Error renaming {filename}: {e}")

    log_file.close()

if __name__ == "__main__":
    directory = input("Enter the directory path: ")
    rename_files(directory)