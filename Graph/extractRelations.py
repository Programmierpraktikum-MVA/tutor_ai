from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np
import time

from preprocessing import process_transcripts

# Verwenden Sie ein vortrainiertes NER-Modell
ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased')
sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


def extract_entities(text):
    entities = ner_model(text)
    return entities

def compute_similarity(sentences, file_name='cosine_scores', batch_size=500):
    print(len(sentences))
    # Berechne die Embeddings für alle Sätze in Batches
    embeddings = []
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i+batch_size]
        batch_embeddings = sentence_model.encode(batch, convert_to_tensor=True)
        embeddings.append(batch_embeddings.cpu().numpy())
    embeddings = np.vstack(embeddings)

    # Berechne die Cosine-Similarity-Matrix in Batches
    cosine_scores = np.empty((len(sentences), len(sentences)), dtype=np.float32)
    for i in range(0, len(sentences), batch_size):
        for j in range(0, len(sentences), batch_size):
            batch_i = embeddings[i:i+batch_size]
            batch_j = embeddings[j:j+batch_size]
            scores = util.pytorch_cos_sim(batch_i, batch_j).cpu().numpy()
            cosine_scores[i:i+batch_size, j:j+batch_size] = scores

    # Speichern der Cosine-Similarity-Matrix in einer Datei
    np.save(file_name, cosine_scores)


def load_and_process_cosine_scores(filename='cosine_scores.dat', threshold=0.8):
    start_time = time.time()
    # Laden der Cosine-Similarity-Matrix
    cosine_scores = np.load(filename)

    # Setzen der Werte unterhalb des Schwellenwerts auf 0
    np.place(cosine_scores, cosine_scores < threshold, 0)

    np.save(filename, cosine_scores)
    end_time = time.time()
    print(f"load_and_process_cosine_scores duration: {end_time - start_time} seconds")




def remove_high_similarity_entries(filename='cosine_scores.npy', threshold=0.95):
    start_time = time.time()
    # Laden der Cosine-Similarity-Matrix
    cosine_scores = np.load(filename)

    print("this many sentences: " + str(cosine_scores.shape[0]))

    # Finden der Indizes, die die Bedingung erfüllen (cosine_scores > threshold) und (i != j)
    indices = np.argwhere(
        (cosine_scores > threshold) & (np.arange(cosine_scores.shape[0])[:, None] != np.arange(cosine_scores.shape[1])))

    # Finden der Indizes, die entfernt werden sollen
    high_similarity_indices = set(j for i, j in indices)
    print("Removed" + str(len(high_similarity_indices)) + "from cosine similarity matrix")

    # Erstellen der neuen Matrix ohne die hohen Ähnlichkeitsindizes
    remaining_indices = sorted(set(range(cosine_scores.shape[0])) - high_similarity_indices)
    new_cosine_scores = cosine_scores[np.ix_(remaining_indices, remaining_indices)]

    # Speichern der neuen Matrix
    np.save(filename, new_cosine_scores)
    end_time = time.time()
    print(f"remove_high_similarity_entries duration: {end_time - start_time} seconds")
    return high_similarity_indices



def load_similarity(file_path, num_sentences, batch_size=100):
    cosine_scores = np.memmap(file_path, dtype='float32', mode='r', shape=(num_sentences, num_sentences))
    return cosine_scores


def get_similarity_value(cosine_scores, i, j):
    return cosine_scores[i, j]


#sentences = process_transcripts('transcripts')
#print("Jetzt cosine stuff")
#compute_similarity([s for s, _ in sentences], 'cosine_stuff_temp')
#remove_high_similarity_entries('D:/saved_edges/cosine_stuff.npy')
#print("jetzt load and process")
#print(load_and_process_cosine_scores('D:/saved_edges/cosine_stuff.npy'))