import spacy
import os
import json
from spacypdfreader import pdf_reader
from spacypdfreader.parsers.pytesseract import PytesseractParser

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


# pip install 'spacypdfreader[pytesseract]'
# python -m spacy download de_core_news_sm
def preprocess_pdf_data(pdf_data_dir):

    course_dict = {} # Creates a dictionary for all courses
    folders = os.listdir(pdf_data_dir)  # Lists all the folders
    for course_folder in folders:
        folder_path = os.path.join(pdf_data_dir, course_folder)
        all_courses = os.listdir(folder_path)  # Lists all the courses

        # Add course ID to dict if necessary
        course_id = os.path.basename(course_folder)
        if course_id not in course_dict:
            course_dict[course_id] = []

        if len(all_courses) != 0:
            for course in all_courses:
                course_path = os.path.join(folder_path, course)
                # TODO: decide on a processing strategy for pdf_data


        break # break the outer for loop for testing



if __name__ == '__main__':  # Main for testing
    pdf_data_dir = "/home/tomklein/Downloads/pdf_data"
    preprocess_pdf_data(pdf_data_dir)
