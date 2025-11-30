import torch
import networkx as nx
import matplotlib.pyplot as plt
from torch_geometric.data import Data


def load_graph(file_path, device):
    graph_data = torch.load(file_path, map_location=device)
    print(f"Graph loaded from {file_path}")
    return graph_data


def visualize_graph(graph_data):
    G = nx.Graph()

    # Knoten hinzufügen
    num_nodes = graph_data.x.shape[0]
    for i in range(num_nodes):
        G.add_node(i)

    # Kanten hinzufügen
    edge_index = graph_data.edge_index.cpu().numpy()
    edge_attr = graph_data.edge_attr.cpu().numpy()
    num_edges = edge_index.shape[0]

    print(f"Number of nodes: {num_nodes}")
    print(f"Number of edges: {num_edges}")

    for i in range(num_edges):
        source = edge_index[i, 0]
        target = edge_index[i, 1]
        weight = edge_attr[i]
        G.add_edge(source, target, weight=weight)

    # Zeichnen des Graphen
    plt.figure(figsize=(24, 16))  # Größeres Layout für bessere Übersicht
    pos = nx.spring_layout(G, k=0.1)  # Layout für die Knotenpositionen
    nx.draw(G, pos, with_labels=True, node_size=500, node_color="lightblue", font_size=8, font_weight="bold",
            edge_color="gray")

    # Zeichnen der Kantenattribute (Ähnlichkeitswerte)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red')

    plt.title("Knowledge Graph Visualization")
    plt.show()


def main():
    # Überprüfen Sie die Verfügbarkeit der GPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Laden des Graphen
    graph_data = load_graph('graph_data.pth', device)

    # Visualisieren des Graphen
    visualize_graph(graph_data)


if __name__ == "__main__":
    main()
