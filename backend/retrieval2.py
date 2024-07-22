import json
import numpy as np
import torch
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

# Initialisiere Modelle
def initialize_models():
    tokenizer = BertTokenizer.from_pretrained('bert-base-german-cased')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    bert_model = BertModel.from_pretrained('bert-base-german-cased').to(device)
    return tokenizer, device, bert_model

# Berechne relevante Embeddings
def get_relevant_embeddings(question_embedding, graph_embeddings, top_k=5):
    similarities = cosine_similarity(question_embedding.reshape(1, -1), graph_embeddings)
    top_indices = similarities.argsort()[0][-top_k:]
    return top_indices

# Wandle Frage in ein Embedding um
def question_to_embedding(question, tokenizer, bert_model, device):
    inputs = tokenizer(question, return_tensors='pt', truncation=True, padding=True, max_length=512).to(device)
    with torch.no_grad():
        outputs = bert_model(**inputs)
        question_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
    return question_embedding

# Extrahiere den Text aus den Embeddings
def extract_text_from_embeddings(raw_data, indices):
    return [raw_data[i]['text'] for i in indices]

# Extrahiere die Embeddings der Texte
def extract_embeddings_from_texts(raw_data, indices):
    return [raw_data[i]['embedding'] for i in indices]

# Erstelle den kombinierten Input mit Kennzeichnung der Texte
def create_combined_input(question, relevant_texts):
    combined_text = question + "\n"  
    for i, text in enumerate(relevant_texts, start=1):
        combined_text += f"Text{i}: {text}\n"  
    return combined_text.strip()

# JSON-Datei laden
with open('data/node_data.json', 'r') as f:
    raw_data = json.load(f)

# Extrahiere die Embeddings und Texte
graph_embeddings = np.array([entry['embedding'] for entry in raw_data])

# Initialisiere Modelle
tokenizer, device, bert_model = initialize_models()

# Wandle eine Frage in ein Embedding um
question = "Was ist Fragmentierung?"
question_embedding = question_to_embedding(question, tokenizer, bert_model, device)

# Zeige das Embedding der Frage an
print("Embedding der Frage:")
print(question_embedding)

# Finde relevante Embeddings
top_k = 3
relevant_indices = get_relevant_embeddings(question_embedding, graph_embeddings, top_k)

# Extrahiere relevante Texte und deren Embeddings
relevant_texts = extract_text_from_embeddings(raw_data, relevant_indices)
relevant_embeddings = extract_embeddings_from_texts(raw_data, relevant_indices)

# Zeige relevante Texte und deren Embeddings an
print("\nRelevante Texte und deren Embeddings:")
for idx, (text, embedding) in enumerate(zip(relevant_texts, relevant_embeddings)):
    print(f"\nText {idx + 1}:")
    print(text)
    print("Embedding:")
    print(embedding)

# Erstelle und zeige den kombinierten Input an
combined_input = create_combined_input(question, relevant_texts)
print("\nKombinierter Input:", combined_input)
