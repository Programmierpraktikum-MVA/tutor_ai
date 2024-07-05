from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np

# Verwenden Sie ein vortrainiertes NER-Modell
ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased')
sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


def extract_entities(text):
    entities = ner_model(text)
    return entities


def compute_similarity(sentences, batch_size=100, output_file='cosine_scores.dat'):
    embeddings = sentence_model.encode(sentences, convert_to_tensor=True)
    num_sentences = len(sentences)

    # Speichern Sie die Cosine Similarity direkt auf der Festplatte
    cosine_scores = np.memmap(output_file, dtype='float32', mode='w+', shape=(num_sentences, num_sentences))

    try:
        for i in range(0, num_sentences, batch_size):
            for j in range(0, num_sentences, batch_size):
                batch_i = embeddings[i:i + batch_size]
                batch_j = embeddings[j:j + batch_size]
                similarity = util.pytorch_cos_sim(batch_i, batch_j).cpu().numpy()

                # Speichern der Ergebnisse in die `cosine_scores` Datei
                cosine_scores[i:i + batch_size, j:j + batch_size] = similarity
    finally:
        # Stellen Sie sicher, dass die Datei korrekt geschlossen wird
        del cosine_scores

    return output_file


def load_similarity(file_path, num_sentences, batch_size=100):
    cosine_scores = np.memmap(file_path, dtype='float32', mode='r', shape=(num_sentences, num_sentences))
    return cosine_scores


def get_similarity_value(cosine_scores, i, j):
    return cosine_scores[i, j]
