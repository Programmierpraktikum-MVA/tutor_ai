import json

def save_edges(all_edges, filename='edges.json'):
    with open(filename, 'w') as f:
        json.dump(all_edges, f)
    print(f"Edges saved to {filename}")

def save_edge_attrs(all_edge_attrs, filename='edge_attrs.json'):
    with open(filename, 'w') as f:
        json.dump(all_edge_attrs, f)
    print(f"Edge attributes saved to {filename}")

def save_node_texts(node_texts, filename='node_texts.json'):
    with open(filename, 'w') as f:
        json.dump(node_texts, f)
    print(f"Node texts saved to {filename}")

def save_node_types(node_types, filename='node_types.json'):
    with open(filename, 'w') as f:
        json.dump(node_types, f)
    print(f"Node types saved to {filename}")

def save_module_numbers(module_numbers, filename='module_numbers.json'):
    with open(filename, 'w') as f:
        json.dump(module_numbers, f)
    print(f"Module numbers saved to {filename}")
