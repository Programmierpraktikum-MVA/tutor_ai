import torch
from torch_geometric.data import Data

def create_graph(node_features, edge_index):
    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
    x = torch.tensor(node_features, dtype=torch.float)

    data = Data(x=x, edge_index=edge_index)
    return data

def add_sentence_to_graph(graph_data, all_nodes, sentence_start_indices, new_entities, new_relations):
    new_start_index = len(all_nodes)
    all_nodes.extend(new_entities)

    new_edges = torch.tensor(new_relations, dtype=torch.long).t().contiguous()
    if new_edges.numel() > 0:
        new_edges = new_edges + new_start_index

    graph_data.edge_index = torch.cat([graph_data.edge_index, new_edges], dim=1)

    sentence_start_indices.append(new_start_index)
    inter_sentence_edge = torch.tensor([[sentence_start_indices[-2]], [new_start_index]], dtype=torch.long)
    graph_data.edge_index = torch.cat([graph_data.edge_index, inter_sentence_edge], dim=1)

    graph_data.x = torch.cat([graph_data.x, torch.tensor(new_entities, dtype=torch.float)], dim=0)

    return graph_data, all_nodes, sentence_start_indices

# Beispiel für die Erstellung und Aktualisierung des Graphen
if __name__ == "__main__":
    entities = [[1], [2]]  # Beispiel Entitäten als Dummy-Features
    relations = [(0, 1)]

    graph_data = create_graph(entities, relations)
    print("Initialer Graph:", graph_data)

    new_entities = [[3], [4]]
    new_relations = [(0, 1)]

    graph_data, all_nodes, sentence_start_indices = add_sentence_to_graph(graph_data, entities, [0], new_entities, new_relations)
    print("Aktualisierter Graph:", graph_data)
