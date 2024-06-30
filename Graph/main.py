import os
import spacy
import torch
from transformers import pipeline
from preprocessing import preprocess_transcripts
from extractRelations import extract_entities, extract_relations
from createGraph import create_graph, add_sentence_to_graph


def initialize_models():
    nlp = spacy.load('de_core_news_sm')
    ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased')
    return nlp, ner_model


def process_transcripts(transcripts_folder, nlp):
    sentences = preprocess_transcripts(transcripts_folder)
    return sentences


def create_initial_graph(sentences, nlp, ner_model):
    all_nodes = []
    all_edges = []
    sentence_start_indices = []

    for sentence in sentences:
        doc = nlp(sentence)
        entities = extract_entities(sentence)
        entity_indices = list(range(len(all_nodes), len(all_nodes) + len(entities)))
        relations = extract_relations(doc)

        start_index = len(all_nodes)
        sentence_start_indices.append(start_index)

        all_nodes.extend([1 for _ in entities])  # Dummy-Features für Entitäten
        edges = torch.tensor(relations, dtype=torch.long).t().contiguous()

        if edges.numel() > 0:
            edges = edges + start_index

        all_edges.append(edges)

    # Konkatinieren Sie alle Kanten
    if all_edges:
        all_edges = torch.cat(all_edges, dim=1)

    # Fügen Sie Kanten zwischen den Sätzen hinzu (z.B. von ROOT zu ROOT)
    inter_sentence_edges = []
    for i in range(len(sentence_start_indices) - 1):
        from_index = sentence_start_indices[i]
        to_index = sentence_start_indices[i + 1]
        inter_sentence_edges.append((from_index, to_index))

    if inter_sentence_edges:
        inter_sentence_edges = torch.tensor(inter_sentence_edges, dtype=torch.long).t().contiguous()
        all_edges = torch.cat([all_edges, inter_sentence_edges], dim=1)

    # Erstellen Sie den Graphen
    graph_data = create_graph(all_nodes, all_edges)
    return graph_data, all_nodes, sentence_start_indices


def update_graph_with_new_sentence(graph_data, nlp, all_nodes, sentence_start_indices, sentence, ner_model):
    doc = nlp(sentence)
    entities = extract_entities(sentence)
    new_entities = [1 for _ in entities]  # Dummy-Features für neue Entitäten
    new_relations = extract_relations(doc)

    graph_data, all_nodes, sentence_start_indices = add_sentence_to_graph(
        graph_data, all_nodes, sentence_start_indices, new_entities, new_relations
    )
    return graph_data, all_nodes, sentence_start_indices


def save_graph(graph_data, file_path):
    torch.save(graph_data, file_path)
    print(f"Graph saved to {file_path}")


def load_graph(file_path):
    graph_data = torch.load(file_path)
    print(f"Graph loaded from {file_path}")
    return graph_data


def main():
    # Initialisieren Sie Modelle
    nlp, ner_model = initialize_models()

    # Laden Sie die Transkripte
    transcripts_folder = 'transcripts'
    sentences = process_transcripts(transcripts_folder, nlp)

    # Erstellen Sie den initialen Graphen
    graph_data, all_nodes, sentence_start_indices = create_initial_graph(sentences, nlp, ner_model)

    # Speichern des Graphen
    save_graph(graph_data, 'graph_data.pth')

    # Laden des Graphen
    loaded_graph_data = load_graph('graph_data.pth')

    print("Finaler Graph:", loaded_graph_data)


if __name__ == "__main__":
    main()
