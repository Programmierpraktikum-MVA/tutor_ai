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

# Beispiel für das Extrahieren von Entitäten und Berechnen der Ähnlichkeit
if __name__ == "__main__":
    import spacy
    nlp = spacy.load('de_core_news_sm')

    text = "Die Informatik ist ein spannendes Fachgebiet. Informatik ist die Wissenschaft von der systematischen Verarbeitung von Informationen."

    # Extrahieren von Entitäten
    entities = extract_entities(text)
    print("Entitäten:", entities)

    # Berechnen der Ähnlichkeit
    sentences = [sent.text for sent in nlp(text).sents]
    similarity = compute_similarity(sentences)
    print("Ähnlichkeit:", similarity)
