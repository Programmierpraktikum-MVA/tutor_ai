import os
import time
import queue
import dropbox
import json
import requests
import logging
import traceback
import requests.exceptions
import dropbox.exceptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    logging.info(f"Uploaded {local_file_path} to Dropbox as {dropbox_path}")

def process_queue(file_queue):
    logging.info("Start processing queue")
    config_data = load_config()

    REFRESH_TOKEN = config_data['DROPBOX_REFRESH_TOKEN']
    APP_KEY = config_data['APP_KEY']
    APP_SECRET = config_data['APP_SECRET']

    access_token = refresh_access_token(REFRESH_TOKEN, APP_KEY, APP_SECRET)
    dbx = dropbox.Dropbox(access_token)

    while True:
        if not file_queue.empty():
            file_path = file_queue.get()

            if file_path == "end.txt":
                break

            if os.path.exists(file_path):
                try:
                    upload_to_dropbox(file_path, f"/{file_path}", dbx)
                except dropbox.exceptions.AuthError as e:
                    logging.error(f"AuthError: {e}")
                    logging.info("Refreshing access token")
                    try:
                        access_token = refresh_access_token(REFRESH_TOKEN, APP_KEY, APP_SECRET)
                        dbx = dropbox.Dropbox(access_token)
                        upload_to_dropbox(file_path, f"/{file_path}", dbx)
                    except Exception as e:
                        logging.error(f"Failed to refresh access token: {e}")
                except (requests.exceptions.RequestException, dropbox.exceptions.ApiError) as e:
                    logging.error(f"Network error while uploading {file_path}: {e}")
                    logging.debug(traceback.format_exc())
                    # Implement retry logic
                    retry_attempts = 3
                    for attempt in range(retry_attempts):
                        try:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            upload_to_dropbox(file_path, f"/{file_path}", dbx)
                            break
                        except (requests.exceptions.RequestException, dropbox.exceptions.ApiError) as retry_e:
                            logging.error(f"Retry {attempt + 1} failed for {file_path}: {retry_e}")
                            logging.debug(traceback.format_exc())
                            if attempt == retry_attempts - 1:
                                logging.error(f"Failed to upload {file_path} after {retry_attempts} attempts")
                except Exception as e:
                    logging.error(f"Failed to upload {file_path}: {e}")
                    logging.debug(traceback.format_exc())
            else:
                logging.warning(f"File {file_path} does not exist")
        time.sleep(1)

# Example usage
if __name__ == "__main__":
    file_queue = queue.Queue()
    # Add files to the queue for testing purposes
    file_queue.put('testfile1.txt')
    file_queue.put('testfile2.txt')
    file_queue.put('end.txt')

    process_queue(file_queue)
