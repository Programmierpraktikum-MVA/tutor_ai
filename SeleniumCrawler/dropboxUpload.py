import os
import time
import queue
import dropbox
import json
def upload_to_dropbox(local_file_path, dropbox_path, dbx):
    with open(local_file_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path)
        os.remove(local_file_path)
    print(f"Uploaded {local_file_path} to Dropbox as {dropbox_path}")


def process_queue(file_queue):
    with open('config.json') as config_file:
        config_data = json.load(config_file)

    # Extract username and password from config data
    dropboxToken = config_data['DROPBOX_ACCESS_TOKEN']
    dbx = dropbox.Dropbox(dropboxToken)
    while True:
        if not file_queue.empty():
            file_name = file_queue.get()

            if(file_name == "end.txt"):
                break

            if os.path.exists(file_name):
                upload_to_dropbox(file_name, f"/{file_name}", dbx)
            else:
                print(f"File {file_name} does not exist")
        time.sleep(1)
