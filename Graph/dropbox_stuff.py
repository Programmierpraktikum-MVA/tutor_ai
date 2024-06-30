import os
import dropbox
import json
import requests
import logging

def load_config():
    with open('config.json') as config_file:
        return json.load(config_file)

def refresh_access_token(refresh_token, app_key, app_secret):
    token_url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': app_key,
        'client_secret': app_secret,
    }

    response = requests.post(token_url, data=data)
    tokens = response.json()
    if 'access_token' in tokens:
        return tokens['access_token']
    else:
        raise Exception(f"Failed to refresh access token: {tokens}")

def download_json_files_from_dropbox(dbx, dropbox_folder_path, local_folder_path):
    try:
        logging.info(f"Listing folder contents at path: {dropbox_folder_path}")
        result = dbx.files_list_folder(dropbox_folder_path, recursive=True)

        # Iterate over each entry
        for entry in result.entries:
            # Check if the entry is a file and ends with .json
            if isinstance(entry, dropbox.files.FileMetadata) and entry.name.endswith('.json'):
                # Create the local path without preserving the folder structure
                local_path = os.path.join(local_folder_path, os.path.basename(entry.path_lower))

                # Download the file
                with open(local_path, "wb") as f:
                    metadata, res = dbx.files_download(path=entry.path_lower)
                    f.write(res.content)
                logging.info(f"Downloaded {entry.name} to {local_path}")

    except dropbox.exceptions.ApiError as err:
        logging.error(f"Failed to list folder contents: {err}")

def list_dropbox_paths(dbx, dropbox_folder_path):
    try:
        logging.info(f"Listing folder contents at path: {dropbox_folder_path}")
        result = dbx.files_list_folder(dropbox_folder_path, recursive=True)

        for entry in result.entries:
            logging.info(f"Found: {entry.path_lower}")

    except dropbox.exceptions.ApiError as err:
        logging.error(f"Failed to list folder contents: {err}")

def start_this():
    logging.info("Start processing queue")
    config_data = load_config()

    REFRESH_TOKEN = config_data['DROPBOX_REFRESH_TOKEN']
    APP_KEY = config_data['APP_KEY']
    APP_SECRET = config_data['APP_SECRET']

    access_token = refresh_access_token(REFRESH_TOKEN, APP_KEY, APP_SECRET)
    dbx = dropbox.Dropbox(access_token)

    DROPBOX_FOLDER_PATH = config_data['DROPBOX_FOLDER_PATH']
    LOCAL_FOLDER_PATH = config_data['LOCAL_FOLDER_PATH']

    download_json_files_from_dropbox(dbx, DROPBOX_FOLDER_PATH, LOCAL_FOLDER_PATH)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    print("start")
    start_this()
