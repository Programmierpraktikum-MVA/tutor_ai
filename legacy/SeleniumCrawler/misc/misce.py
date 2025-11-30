import os
import json
def ensure_json_file_exists(file_path):
    """
    Check if a JSON file exists. If not, create an empty JSON file.
    """
    if not os.path.exists(file_path):
        # If the file does not exist, create it with an empty list
        with open(file_path, 'w') as file:
            json.dump([], file)
        print(f"Created a new JSON file at {file_path}")
    else:
        print(f"JSON file already exists at {file_path}")


# Function to load JSON data from a file
def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)
# Function to check if the URL exists in the JSON data
def url_exists(file_path, url):
    try:
        data = load_json(file_path)
        for entry in data:
            if entry.get("Link") == url:
                return True
        return False
    except json.JSONDecodeError as e:
        print(f"Error reading JSON file: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False