import spacy
import os
import json

# Laden Sie das SpaCy Deutschmodell
nlp = spacy.load('de_core_news_sm')


def process_transcripts(transcripts_folder):
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


def preprocess_email_data(mails_file):
    with open(mails_file, 'r', encoding='utf-8') as f:
        mails = json.load(f)

    processed_mails = []
    for mail in mails:
        subject = mail.get('subject', '')
        sender = mail.get('sender', '')
        body = mail.get('body', '')
        recipients = mail.get('recipients', [])
        date = mail.get('date', '')
        processed_mails.append((subject, sender, body, recipients, date))

    return processed_mails
