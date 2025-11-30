import json
import numpy as np


def save_edges(all_edges, file_path='D:/saved_edges/edges.json'):
    # Convert numpy.int64 elements to int
    converted_edges = [(int(edge[0]), int(edge[1])) for edge in all_edges]

    # Save the converted edges to a file
    with open(file_path, 'w') as f:
        json.dump(converted_edges, f)


def load_edges(file_path='D:/saved_edges/edges.json'):
    with open(file_path, 'r') as f:
        edges = json.load(f)
    return [(tuple(edge)) for edge in edges]


def save_edge_attrs(all_edge_attrs, filename='D:/saved_edges/edge_attrs.json'):
    with open(filename, 'w') as f:
        json.dump(all_edge_attrs, f)
    print(f"Edge attributes saved to {filename}")


def load_edge_attrs(filename='D:/saved_edges/edge_attrs.json'):
    with open(filename, 'r') as f:
        edge_attrs = json.load(f)
    return edge_attrs


def save_node_texts(node_texts, filename='D:/saved_edges/node_texts.json'):
    with open(filename, 'w') as f:
        json.dump(node_texts, f)
    print(f"Node texts saved to {filename}")


def load_node_texts(filename='D:/saved_edges/node_texts.json'):
    with open(filename, 'r') as f:
        node_texts = json.load(f)
    return node_texts


def save_node_types(node_types, filename='D:/saved_edges/node_types.json'):
    with open(filename, 'w') as f:
        json.dump(node_types, f)
    print(f"Node types saved to {filename}")


def load_node_types(filename='D:/saved_edges/node_types.json'):
    with open(filename, 'r') as f:
        node_types = json.load(f)
    return node_types


def save_module_numbers(module_numbers, filename='D:/saved_edges/module_numbers.json'):
    with open(filename, 'w') as f:
        json.dump(module_numbers, f)
    print(f"Module numbers saved to {filename}")


def load_module_numbers(filename='D:/saved_edges/module_numbers.json'):
    with open(filename, 'r') as f:
        module_numbers = json.load(f)
    return module_numbers

# Example usage
if __name__ == "__main__":

    loaded_edges = load_edges()
    loaded_edge_attrs = load_edge_attrs()
    loaded_node_texts = load_node_texts()
    loaded_node_types = load_node_types()
    loaded_module_numbers = load_module_numbers()

    print("Loaded edges:", loaded_edges)
    print("Loaded edge attributes:", loaded_edge_attrs)
    print("Loaded node texts:", loaded_node_texts)
    print("Loaded node types:", loaded_node_types)
    print("Loaded module numbers:", loaded_module_numbers)
