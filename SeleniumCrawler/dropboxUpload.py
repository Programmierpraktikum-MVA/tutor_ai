import os
import time
import queue
import dropbox
import json
import requests

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

def upload_to_dropbox(local_file_path, dropbox_path, dbx):
    with open(local_file_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path)
    os.remove(local_file_path)
    print(f"Uploaded {local_file_path} to Dropbox as {dropbox_path}")

def process_queue(file_queue):
    print("start process_queue")
    config_data = load_config()

    REFRESH_TOKEN = config_data['DROPBOX_REFRESH_TOKEN']
    APP_KEY = config_data['APP_KEY']
    APP_SECRET = config_data['APP_SECRET']

    access_token = refresh_access_token(REFRESH_TOKEN, APP_KEY, APP_SECRET)
    dbx = dropbox.Dropbox(access_token)

    while True:
        if not file_queue.empty():
            file_name = file_queue.get()

            if file_name == "end.txt":
                break

            if os.path.exists(file_name):
                try:
                    upload_to_dropbox(file_name, f"/{file_name}", dbx)
                except dropbox.exceptions.AuthError as e:
                    print(f"AuthError: {e}")
                    # Refresh the access token if it expires
                    access_token = refresh_access_token(REFRESH_TOKEN, APP_KEY, APP_SECRET)
                    dbx = dropbox.Dropbox(access_token)
                    upload_to_dropbox(file_name, f"/{file_name}", dbx)
            else:
                print(f"File {file_name} does not exist")
        time.sleep(1)

# Example usage
if __name__ == "__main__":
    file_queue = queue.Queue()
    # Add files to the queue for testing purposes
    file_queue.put('testfile1.txt')
    file_queue.put('testfile2.txt')
    file_queue.put('end.txt')

    process_queue(file_queue)
