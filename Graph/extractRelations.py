from transformers import pipeline

# Verwenden Sie ein vortrainiertes NER-Modell
ner_model = pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')

def extract_entities(text):
    entities = ner_model(text)
    return entities

def extract_relations(doc):
    relations = []
    for token in doc:
        if token.dep_ != "ROOT":
            relation = (token.head.i, token.i)  # Speichern der Indizes des Kopfes und des Tokens
            relations.append(relation)
    return relations

# Beispiel für das Extrahieren von Entitäten und Relationen
if __name__ == "__main__":
    import spacy
    nlp = spacy.load('de_core_news_sm')

    text = "Alan Turing ist der Vater der Informatik."

    # Extrahieren von Entitäten
    entities = extract_entities(text)
    print("Entitäten:", entities)

    # Verarbeiten des Textes mit SpaCy
    doc = nlp(text)

    # Extrahieren von Relationen
    relations = extract_relations(doc)
    print("Relationen:", relations)
