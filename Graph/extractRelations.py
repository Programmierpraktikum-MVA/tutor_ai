from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

# Verwenden Sie ein vortrainiertes NER-Modell
ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased')
sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def extract_entities(text):
    entities = ner_model(text)
    return entities

def compute_similarity(sentences):
    embeddings = sentence_model.encode(sentences, convert_to_tensor=True)
    cosine_scores = util.pytorch_cos_sim(embeddings, embeddings)
    return cosine_scores
