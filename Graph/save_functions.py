import json

def save_edges(all_edges, filename='D:/saved_edges/edges.json'):
    with open(filename, 'w') as f:
        json.dump(all_edges, f)
    print(f"Edges saved to {filename}")

def save_edge_attrs(all_edge_attrs, filename='D:/saved_edges/edge_attrs.json'):
    with open(filename, 'w') as f:
        json.dump(all_edge_attrs, f)
    print(f"Edge attributes saved to {filename}")

def save_node_texts(node_texts, filename='D:/saved_edges/node_texts.json'):
    with open(filename, 'w') as f:
        json.dump(node_texts, f)
    print(f"Node texts saved to {filename}")

def save_node_types(node_types, filename='D:/saved_edges/node_types.json'):
    with open(filename, 'w') as f:
        json.dump(node_types, f)
    print(f"Node types saved to {filename}")

def save_module_numbers(module_numbers, filename='D:/saved_edges/module_numbers.json'):
    with open(filename, 'w') as f:
        json.dump(module_numbers, f)
    print(f"Module numbers saved to {filename}")
