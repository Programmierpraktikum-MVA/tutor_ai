import torch
from torch_geometric.data import Data
from torch_geometric.utils import add_remaining_self_loops
from extractRelations import compute_similarity
from transformers import BertModel, BertTokenizer

def create_graph(edge_index, edge_attr, node_texts, node_types, module_numbers, tokenizer, bert_model, device):
    print("DAS HIER IST EDGE_INDEX DAVOR!!!")
    print(edge_index)
    print("\n\n\n")
    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous().to(device)
    print(f"edge_index values: {edge_index}")  # Debugging-Information

    # BERT-Embeddings für node_texts
    text_embeddings = []
    for text in node_texts:
        inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512).to(device)
        outputs = bert_model(**inputs)
        text_embeddings.append(outputs.last_hidden_state.mean(dim=1).squeeze().detach())

    text_embeddings = torch.stack(text_embeddings).to(device)

    # One-Hot-Encoding für node_types
    unique_types = list(set(node_types))
    type_to_index = {type_: idx for idx, type_ in enumerate(unique_types)}
    type_embeddings = torch.tensor([type_to_index[type_] for type_ in node_types], dtype=torch.long).to(device)
    type_embeddings = torch.nn.functional.one_hot(type_embeddings, num_classes=len(unique_types)).float().to(device)

    # One-Hot-Encoding für module_numbers
    unique_modules = list(set(module_numbers))
    module_to_index = {module: idx for idx, module in enumerate(unique_modules)}
    module_embeddings = torch.tensor([module_to_index[module] for module in module_numbers], dtype=torch.long).to(device)
    module_embeddings = torch.nn.functional.one_hot(module_embeddings, num_classes=len(unique_modules)).float().to(device)

    # Zusammenführen der Embeddings
    node_features = torch.cat([text_embeddings, type_embeddings, module_embeddings], dim=1).to(device)

    data = Data(x=node_features, edge_index=edge_index)
    data.edge_attr = edge_attr
    data.node_texts = node_texts
    data.node_types = node_types
    data.module_numbers = module_numbers
    data.type_to_index = type_to_index  # Speichern des Mappings für spätere Verwendung

    # Debugging von edge_index
    print(f"edge_index before self-loops: {data.edge_index.shape}")  # Debugging-Information

    # Hinzufügen von Selbstschleifen
    data.edge_index, _ = add_remaining_self_loops(data.edge_index, num_nodes=data.x.size(0))

    # Debugging nach dem Hinzufügen von Selbstschleifen
    print(f"edge_index after self-loops: {data.edge_index.shape}")  # Debugging-Information
    print(f"edge_index values after self-loops: {data.edge_index}")  # Debugging-Information

    return data

def create_node_base_mails(mail_array):
    all_edges = []
    all_edge_attrs = []
    node_texts = []
    node_types = []
    module_numbers = []

    node_id = 0

    for subject, sender, body, recipients, date in mail_array:
        # Create nodes for each email attribute
        subject_node = node_id
        sender_node = node_id + 1
        body_node = node_id + 2
        recipient_nodes = list(range(node_id + 3, node_id + 3 + len(recipients)))
        date_node = node_id + 3 + len(recipients)

        node_texts.extend([subject, sender, body, *recipients, date])
        node_types.extend(['subject', 'sender', 'body', *['recipient'] * len(recipients), 'date'])

        # Create edges from the subject node to other nodes
        all_edges.extend([
            (subject_node, sender_node),
            (subject_node, body_node),
            (subject_node, date_node)
        ] + [(subject_node, recipient_node) for recipient_node in recipient_nodes])

        all_edge_attrs.extend([
            'subject-sender',
            'subject-body',
            'subject-date'
        ] + ['subject-recipient'] * len(recipients))

        node_id = date_node + 1

    module_numbers.extend([0] * node_id)

    return all_edges, all_edge_attrs, node_texts, node_types, module_numbers, node_id

def create_node_base_sentences(sentences):
    all_edges = []
    all_edge_attrs = []
    node_texts = []
    node_types = []
    module_numbers = []

    for sentence, module_number in sentences:
        node_texts.append(sentence)
        node_types.append("Satz")
        module_numbers.append(module_number)

    similarity_matrix = compute_similarity([s for s, _ in sentences], 100)
    threshold = 0.75

    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            if similarity_matrix[i, j] > threshold:
                all_edges.append((i, j))
                all_edge_attrs.append("Similarity" + str(similarity_matrix[i, j].item()))

    for i in range(len(sentences) - 1):
        all_edges.append((i, i + 1))
        all_edge_attrs.append("Sequential")

    return all_edges, all_edge_attrs, node_texts, node_types, module_numbers, len(sentences)

def merge_node_base(all_edges1, all_edge_attrs1, node_texts1, node_types1, module_numbers1, count_1,
                    all_edges2, all_edge_attrs2, node_texts2, node_types2, module_numbers2, count_2):
    adjusted_edges2 = [(edge[0] + count_1, edge[1] + count_1) for edge in all_edges2]
    all_edges1.extend(adjusted_edges2)
    all_edge_attrs1.extend(all_edge_attrs2)
    node_texts1.extend(node_texts2)
    node_types1.extend(node_types2)
    module_numbers1.extend(module_numbers2)

    return all_edges1, all_edge_attrs1, node_texts1, node_types1, module_numbers1, count_1 + count_2



def save_graph(graph_data, file_path):
    torch.save(graph_data, file_path)
    print(f"Graph saved to {file_path}")

def load_graph(file_path, device):
    graph_data = torch.load(file_path, map_location=device)
    print(f"Graph loaded from {file_path}")
    return graph_data
