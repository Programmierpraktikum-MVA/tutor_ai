import whisper_timestamped as whisper
import time
import os
import json

MODELSIZE = "small"

def transcribe_audio(file_path, file_name, folder_path):
    print("Called Transcribe_audio")
    now = time.time()
    audio = whisper.load_audio(file_path)
    model = whisper.load_model(MODELSIZE, device="cuda")
    print(f"Loading the audio and model took {time.time() - now} seconds")
    now = time.time()
    result = model.transcribe(file_path)
    print(f"Transcription took {time.time() - now} seconds")
    filename = os.path.basename(file_path)
    filename_without_ext = os.path.splitext(filename)[0]

    # Create a dictionary with lecture and Timestamps
    data = {
        "lecture": filename_without_ext,
        "Timestamps": clean_transcriptions(create_segment(result))
    }

    # Define the path for the transcriptions.json file
    json_file_path = f'{folder_path}/{file_name}.json'

    # Check if the file exists, if not create it and write the data
    if not os.path.exists(json_file_path):
        with open(json_file_path, 'w') as f:
            json.dump([data], f)  # Enclose the data in a list
    else:
    # If the file exists, append the new data
        with open(json_file_path, 'r+') as f:
            existing_data = json.load(f)
            existing_data.append(data)  # Append the new data to the list
            f.seek(0)
            json.dump(existing_data, f)


def create_segment(data):
    new_segments = []
    current_segment = ''
    segment_start = None  # Initialize the start time of the current segment
    for segment in data['segments']:
        text = segment['text']
        if segment_start is None:  # If this is the first segment in the new segment
            segment_start = segment['start']  # Set the start time of the current segment
        if len(current_segment + text) <= 400:
            current_segment += ' ' + text
        else:
            last_period_index = current_segment.rfind('.')
            if last_period_index != -1:
                new_segments.append({
                    'text': current_segment[:last_period_index + 1],
                    'start': segment_start,  # Use the start time of the current segment
                    'end': segment['end']  # Use the end time of the current segment
                })
                current_segment = current_segment[last_period_index + 2:] + ' ' + text
            else:
                new_segments.append({
                    'text': current_segment,
                    'start': segment_start,  # Use the start time of the current segment
                    'end': segment['end']  # Use the end time of the current segment
                })
                current_segment = text
            segment_start = None  # Reset the start time for the next segment
    if current_segment:
        new_segments.append({
            'text': current_segment,
            'start': segment_start,  # Use the start time of the last segment
            'end': data['segments'][-1]['end']  # Use the end time of the last segment
        })
    return new_segments
def clean_transcriptions(json_obj):
    # Define the mapping of characters
    mapping = {
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'ß': 'ss',
        'Ä': 'Ae',
        'Ö': 'Oe',
        'Ü': 'Ue'
    }

    # Check if json_obj is a list of dictionaries
    if isinstance(json_obj, list) and all(isinstance(item, dict) for item in json_obj):
        # Iterate over the items in the json object
        for item in json_obj:
            # Replace the characters in the 'text' field
            for old_char, new_char in mapping.items():
                item['text'] = item['text'].replace(old_char, new_char)
    else:
        raise ValueError("json_obj must be a list of dictionaries with a 'text' key")

    return json_obj
