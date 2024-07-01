import os
import spacy
import torch
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from preprocessing import preprocess_transcripts
from extractRelations import extract_entities, compute_similarity
from createGraph import create_graph, add_sentence_to_graph

def initialize_models(device):
    nlp = spacy.load('de_core_news_sm')
    ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased', device=device)
    sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device)
    return nlp, ner_model, sentence_model

def process_transcripts(transcripts_folder, nlp):
    sentences = preprocess_transcripts(transcripts_folder)
    return sentences

def create_initial_graph(sentences, nlp, ner_model, sentence_model, device):
    all_nodes = []
    all_edges = []
    all_edge_attrs = []
    sentence_start_indices = []

    # Knoten und Dummy-Features für jeden Satz erstellen
    for sentence in sentences:
        all_nodes.append([1])  # Dummy-Feature für jeden Satzknoten

    # Ähnlichkeit zwischen Sätzen berechnen und Kanten erstellen
    similarity_matrix = compute_similarity(sentences)
    threshold = 0.75  # Ähnlichkeitsschwelle für Kanten

    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            if similarity_matrix[i, j] > threshold:
                all_edges.append([i, j])
                all_edge_attrs.append(similarity_matrix[i, j].item())

    # Fügen Sie Kanten für aufeinanderfolgende Sätze hinzu
    for i in range(len(sentences) - 1):
        all_edges.append([i, i + 1])
        all_edge_attrs.append(1.0)  # Ein fester Wert für aufeinanderfolgende Sätze

    # Konkatinieren Sie alle Kanten und deren Attribute
    if all_edges:
        all_edges = torch.tensor(all_edges, dtype=torch.long).t().contiguous().to(device)
        all_edge_attrs = torch.tensor(all_edge_attrs, dtype=torch.float).to(device)

    # Erstellen Sie den Graphen
    graph_data = create_graph(all_nodes, all_edges, all_edge_attrs).to(device)
    return graph_data, all_nodes, sentence_start_indices

def update_graph_with_new_sentence(graph_data, nlp, all_nodes, sentence_start_indices, sentence, ner_model, sentence_model, device):
    doc = nlp(sentence)
    entities = extract_entities(sentence)
    new_entities = [1]  # Dummy-Feature für neuen Satzknoten
    sentence_start_indices.append(len(all_nodes))
    all_nodes.append(new_entities)

    # Ähnlichkeit zwischen neuem Satz und bestehenden Sätzen berechnen
    existing_sentences = [s.text for s in nlp.pipe([s for s in sentences])]
    new_similarity = compute_similarity([sentence] + existing_sentences)[0, 1:]

    new_relations = []
    new_edge_attr = []
    for i, sim in enumerate(new_similarity):
        if sim > 0.75:
            new_relations.append([len(all_nodes) - 1, i])
            new_edge_attr.append(sim.item())

    # Fügen Sie eine Kante für die natürliche Reihenfolge hinzu
    if len(sentence_start_indices) > 1:
        new_relations.append([len(all_nodes) - 2, len(all_nodes) - 1])
        new_edge_attr.append(1.0)

    graph_data, all_nodes, sentence_start_indices = add_sentence_to_graph(
        graph_data, all_nodes, sentence_start_indices, new_entities, new_relations, new_edge_attr
    )
    return graph_data, all_nodes, sentence_start_indices

def save_graph(graph_data, file_path):
    torch.save(graph_data, file_path)
    print(f"Graph saved to {file_path}")

def load_graph(file_path, device):
    graph_data = torch.load(file_path, map_location=device)
    print(f"Graph loaded from {file_path}")
    return graph_data

def main():
    # Überprüfen Sie die Verfügbarkeit der GPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Initialisieren Sie Modelle
    nlp, ner_model, sentence_model = initialize_models(device)

    # Laden Sie die Transkripte
    transcripts_folder = 'transcripts'
    sentences = process_transcripts(transcripts_folder, nlp)

    # Erstellen Sie den initialen Graphen
    graph_data, all_nodes, sentence_start_indices = create_initial_graph(sentences, nlp, ner_model, sentence_model, device)

    # Speichern des Graphen
    save_graph(graph_data, 'graph_data.pth')

    # Laden des Graphen
    loaded_graph_data = load_graph('graph_data.pth', device)

    print("Finaler Graph:", loaded_graph_data)

if __name__ == "__main__":
    main()
