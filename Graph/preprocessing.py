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
            with open(filepath, 'r') as f:
                transcript = json.load(f)
                if isinstance(transcript, list):
                    for entry in transcript:
                        for timestamp in entry['Timestamps']:
                            doc = nlp(timestamp['text'])
                            sentences.extend([sent.text for sent in doc.sents])
    return sentences

# Beispiel für das Laden und Vorverarbeiten von Transkripten
if __name__ == "__main__":
    transcripts_folder = 'transcripts'
    sentences = preprocess_transcripts(transcripts_folder)
    for sent in sentences:
        print(sent)
