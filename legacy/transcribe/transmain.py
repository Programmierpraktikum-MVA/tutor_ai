import subprocess
import os
import json
from transcribe import transcribe_audio

def load_log(log_file):
    if os.path.exists(log_file):
        with open(log_file, 'r') as file:
            return json.load(file)
    return {}


def save_log(log, log_file):
    with open(log_file, 'w') as file:
        json.dump(log, file, indent=4)


def extract_audio(local_video_path, output_file):
    try:
        ffmpeg_command = f'ffmpeg -i "{local_video_path}" -vn -acodec libmp3lame -y "{output_file}"'
        subprocess.call(ffmpeg_command, shell=True)
    except Exception as e:
        print(f"Error during audio extraction: {e}")


def get_folders_and_files(main_folder):
    # List to hold the paths of folders and their respective mp4 files
    folder_file_paths = []

    # Walk through the main folder
    for root, dirs, files in os.walk(main_folder):
        # We only need the first level of directories within the main folder
        if root == main_folder:
            for directory in dirs:
                folder_path = os.path.join(main_folder, directory)
                mp4_files = []

                # List files in the subdirectory
                for file in os.listdir(folder_path):
                    if file.endswith(".mp4"):
                        file_path = os.path.join(folder_path, file)
                        mp4_files.append(file_path)

                # Append the folder path and its mp4 files to the list
                folder_file_paths.append((folder_path, mp4_files))

    return folder_file_paths


def start(main_folder, log_file):
    # Load the log
    log = load_log(log_file)

    # Example usage:
    result = get_folders_and_files(main_folder)
    for folder, files in result:
        print(f"Folder: {folder}")
        temp = folder.split('\\')
        folder_name = temp[-1]
        path = f'audio_files/{folder_name}'
        transcribed_folder_path = f'transcribed/{folder_name}'
        os.makedirs(path, exist_ok=True)
        os.makedirs(transcribed_folder_path, exist_ok=True)
        for file in files:
            if file in log and log[file] == 'transformed':
                print(f"  Skipping already transformed file: {file}")
                continue

            print(f"  File: {file}")
            temp = file.split('\\')
            t2 = temp[-1]
            t2 = t2.split('.')[0]
            file_name = f"{t2}.mp3"
            file_path = f'{path}\\{file_name}'
            extract_audio(file, file_path)
            transcribe_audio(file_path, f'{t2}_transcribed', folder_name)

            # Update the log
            log[file] = 'transformed'
            save_log(log, log_file)



# Example usage
main_folder = '../SeleniumCrawler/downloaded_videos'
log_file = 'transformation_log.json'
start(main_folder, log_file)
