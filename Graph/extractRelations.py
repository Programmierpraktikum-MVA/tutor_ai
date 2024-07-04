from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import torch

# Verwenden Sie ein vortrainiertes NER-Modell
ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased')
sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def extract_entities(text):
    entities = ner_model(text)
    return entities

def compute_similarity(sentences, batch_size):
    embeddings = sentence_model.encode(sentences, convert_to_tensor=True)
    num_sentences = len(sentences)
    cosine_scores = torch.zeros((num_sentences, num_sentences), device=embeddings.device)

    for i in range(0, num_sentences, batch_size):
        for j in range(i, num_sentences, batch_size):
            batch_i = embeddings[i:i+batch_size]
            batch_j = embeddings[j:j+batch_size]
            cosine_scores[i:i+batch_size, j:j+batch_size] = util.pytorch_cos_sim(batch_i, batch_j)

    return cosine_scores
