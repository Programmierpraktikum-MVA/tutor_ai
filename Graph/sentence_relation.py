import spacy
import torch
from torch_geometric.data import Data

# Laden Sie das SpaCy Deutschmodell
nlp = spacy.load("de_core_news_sm")

def extract_relations(doc):
    """
    Extrahiert Relationen zwischen den Wörtern in einem Satz.
    """
    relations = []
    for token in doc:
        if token.dep_ != "ROOT":
            relation = (token.head.i, token.i)  # Speichern der Indizes des Kopfes und des Tokens
            relations.append(relation)
    return relations

def create_initial_graph(sentences):
    """
    Erstellt einen initialen Graphen aus einer Liste von Sätzen.
    """
    all_nodes = []
    all_edges = []
    sentence_start_indices = []

    for sentence in sentences:
        doc = nlp(sentence)
        nodes = [token.text for token in doc]
        relations = extract_relations(doc)

        start_index = len(all_nodes)
        sentence_start_indices.append(start_index)

        all_nodes.extend(nodes)
        edges = torch.tensor(relations, dtype=torch.long).t().contiguous()

        # Verschieben Sie die Kanten-Indizes um den Startindex des aktuellen Satzes
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

    # Erstellen Sie einen Graphen
    x = torch.arange(len(all_nodes)).view(-1, 1)
    data = Data(x=x, edge_index=all_edges)

    return data, all_nodes, sentence_start_indices

def add_sentence_to_graph(graph_data, all_nodes, sentence_start_indices, new_sentence):
    """
    Fügt einen neuen Satz zu einem bestehenden Graphen hinzu.
    """
    new_doc = nlp(new_sentence)
    new_nodes = [token.text for token in new_doc]
    new_relations = extract_relations(new_doc)

    # Update the node indices for the new sentence
    new_start_index = len(all_nodes)
    all_nodes.extend(new_nodes)

    new_edges = torch.tensor(new_relations, dtype=torch.long).t().contiguous()
    if new_edges.numel() > 0:
        new_edges = new_edges + new_start_index

    # Add new edges to existing edges
    graph_data.edge_index = torch.cat([graph_data.edge_index, new_edges], dim=1)

    # Optionally, add edges between the last sentence and the new sentence
    sentence_start_indices.append(new_start_index)
    inter_sentence_edge = torch.tensor([[sentence_start_indices[-2]], [new_start_index]], dtype=torch.long)
    graph_data.edge_index = torch.cat([graph_data.edge_index, inter_sentence_edge], dim=1)

    # Update node features
    graph_data.x = torch.arange(len(all_nodes)).view(-1, 1)

    return graph_data, all_nodes, sentence_start_indices

# Beispiel Sätze
sentences = [
    "Der schnelle braune Fuchs springt über den faulen Hund.",
    "Ein Hund bellt laut, während er den Fuchs beobachtet."
]

# Erstellen Sie den initialen Graphen
graph_data, all_nodes, sentence_start_indices = create_initial_graph(sentences)
print("Initiale Knoten:", all_nodes)
print("Initiale Kanten:", graph_data.edge_index)

# Fügen Sie einen neuen Satz hinzu
new_sentence = "Der Fuchs und der Hund laufen jetzt zusammen."
graph_data, all_nodes, sentence_start_indices = add_sentence_to_graph(graph_data, all_nodes, sentence_start_indices, new_sentence)
print("Aktualisierte Knoten:", all_nodes)
print("Aktualisierte Kanten:", graph_data.edge_index)
