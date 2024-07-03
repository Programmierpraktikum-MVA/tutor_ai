import spacy
import os
import json

# Laden Sie das SpaCy Deutschmodell
nlp = spacy.load('de_core_news_sm')

def preprocess_transcripts(transcripts_folder):
    sentences = []
    for filename in os.listdir(transcripts_folder):
        if filename.endswith('.json'):
            filepath = os.path.join(transcripts_folder, filename)
            module_number = int(filename.split('_')[0])  # Extrahieren der Modulnummer aus dem Dateinamen
            with open(filepath, 'r') as f:
                transcript = json.load(f)
                if isinstance(transcript, list):
                    for entry in transcript:
                        for timestamp in entry['Timestamps']:
                            doc = nlp(timestamp['text'])
                            sentences.extend([(sent.text, module_number) for sent in doc.sents])
    return sentences

def process_transcripts(transcripts_folder, nlp):
    sentences = preprocess_transcripts(transcripts_folder)
    return sentences

def preprocess_email_data(file_name):
    with open(file_name, 'r', encoding='utf-8') as file:
        data = json.load(file)
    email_tuples = []
    for email in data:
        subject = email.get("subject", "")
        sender = email.get("sender", "")
        body = email.get("body", "")
        recipients = email.get("recipients", [])
        date = email.get("date", "")
        email_tuples.append((subject, sender, body, recipients, date))
    return email_tuples

preprocessed_transcripts = preprocess_email_data('mail.json')