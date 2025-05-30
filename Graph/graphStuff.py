import torch
from torch_geometric.data import Data
from torch_geometric.utils import add_remaining_self_loops
from extractRelations import compute_similarity, load_similarity, get_similarity_value, load_and_process_cosine_scores, remove_high_similarity_entries
from transformers import BertModel, BertTokenizer
import os
import json
import numpy as np
import torch
from torch_geometric.data import Data
from torch_geometric.utils import add_remaining_self_loops
from transformers import BertModel, BertTokenizer

from torch_geometric.nn import SAGEConv  # added by tom


def create_graph(edge_index, edge_attr, node_texts, node_types, module_numbers, tokenizer, bert_model, device):
    edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous().to(device)

    # BERT-Embeddings für node_texts
    text_embeddings = []
    for text in node_texts:
        inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512).to(device)
        outputs = bert_model(**inputs)
        text_embeddings.append(outputs.last_hidden_state.mean(dim=1).squeeze().detach())

    text_embeddings = torch.stack(text_embeddings).to(device)
    print(f'Text Embeddings Shape: {text_embeddings.shape}')  # Debugging line

    # One-Hot-Encoding für node_types
    unique_types = list(set(node_types))
    type_to_index = {type_: idx for idx, type_ in enumerate(unique_types)}
    type_embeddings = torch.tensor([type_to_index[type_] for type_ in node_types], dtype=torch.long).to(device)
    type_embeddings = torch.nn.functional.one_hot(type_embeddings, num_classes=len(unique_types)).float().to(device)
    print(f'Type Embeddings Shape: {type_embeddings.shape}')  # Debugging line

    # One-Hot-Encoding für module_numbers
    unique_modules = list(set(module_numbers))
    module_to_index = {module: idx for idx, module in enumerate(unique_modules)}
    module_embeddings = torch.tensor([module_to_index[module] for module in module_numbers], dtype=torch.long).to(device)
    module_embeddings = torch.nn.functional.one_hot(module_embeddings, num_classes=len(unique_modules)).float().to(device)
    print(f'Module Embeddings Shape: {module_embeddings.shape}')  # Debugging line

    # Zusammenführen der Embeddings
    print(f'Before concatenation: Text Embeddings Shape: {text_embeddings.shape}, Type Embeddings Shape: {type_embeddings.shape}, Module Embeddings Shape: {module_embeddings.shape}')  # Debugging line
    node_features = torch.cat([text_embeddings, type_embeddings, module_embeddings], dim=1).to(device)
    print(f'Node Features Shape after concatenation: {node_features.shape}')  # Debugging line

    data = Data(x=node_features, edge_index=edge_index)
    data.edge_attr = edge_attr
    data.node_texts = node_texts
    data.node_types = node_types
    data.module_numbers = module_numbers
    data.type_to_index = type_to_index  # Speichern des Mappings für spätere Verwendung

    # Hinzufügen von Selbstschleifen
    data.edge_index, _ = add_remaining_self_loops(data.edge_index, num_nodes=data.x.size(0))

    return data


# https://medium.com/analytics-vidhya/ohmygraphs-graphsage-in-pyg-598b5ec77e7b
def SAGEconv_layer(data):
    x, edge_index = data.x, data.edge_index

    # TODO: What is input_dim (feature vectors does each node have)?
    input_dim = 3

    # how many feature vectors should the resulting node have?
    output_dim = 2

    conv1 = SAGEConv(input_dim, output_dim)

    # One forward pass
    x = conv1(x, edge_index)
    return x


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


def create_node_base_sentences(sentences, threshold=0.75):
    all_edges = []
    all_edge_attrs = []
    node_texts = []
    node_types = []
    module_numbers = []
    count = 0

    # Einlesen der Cosine-Similarity-Matrix und Anwenden des Schwellenwerts
    compute_similarity([s for s, _ in sentences], 'D:/saved_edges/cosine_scores')
    high_similarity_indices = remove_high_similarity_entries('D:/saved_edges/cosine_scores.npy')
    sentences = [tup for i, tup in enumerate(sentences) if i not in high_similarity_indices]
    load_and_process_cosine_scores('D:/saved_edges/cosine_scores.npy', threshold)
    cosine_scores = np.load('D:/saved_edges/cosine_scores.npy')
    #print(cosine_scores)

    for sentence, module_number in sentences:
        node_texts.append(sentence)
        node_types.append("Satz")
        module_numbers.append(module_number)

    # Erstellen der Kanten basierend auf der Cosine-Similarity-Matrix
    indices = np.argwhere(cosine_scores > 0)
    for i, j in indices:
        if i < j:  # Um doppelte Kanten zu vermeiden
            edge = (i, j)
            attr = cosine_scores[i, j].item()
            all_edges.append(edge)
            all_edge_attrs.append(attr)

    # Fügen Sie Kanten für aufeinanderfolgende Sätze hinzu
    for i in range(len(sentences) - 1):
        edge = (i, i + 1)
        attr = 1.0  # A fixed value for consecutive sentences
        all_edges.append(edge)
        all_edge_attrs.append(attr)

    return all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count


def create_node_base_sentences_cosine_avail(sentences, similarity_file):
    all_edges = []
    all_edge_attrs = []
    node_texts = []
    node_types = []
    module_numbers = []

    for sentence, module_number in sentences:
        node_texts.append(sentence)
        node_types.append("Satz")
        module_numbers.append(module_number)

    num_sentences = len(sentences)
    similarity_matrix = load_similarity(similarity_file, num_sentences)
    threshold = 0.75

    print("mach sim attr")

    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            similarity = get_similarity_value(similarity_matrix, i, j)
            if similarity > threshold:
                all_edges.append((i, j))
                all_edge_attrs.append("Similarity" + str(similarity))

    print("Done sim attr")

    for i in range(len(sentences) - 1):
        all_edges.append((i, i + 1))
        all_edge_attrs.append("Sequential")

    print("done seq")

    return all_edges, all_edge_attrs, node_texts, node_types, module_numbers, len(sentences)


def create_node_base_moses(dir_path):
    count = 0
    all_edges = []
    all_edge_attrs = []
    node_texts = []
    node_types = []
    module_numbers = []
    course_node_id = 0

    course_list = os.listdir(dir_path)
    for course in course_list:
        count = count + 1
        course_node_id = course_node_id + 1

        # Add node for course with its name as text
        node_types.append("Kurs")
        node_texts.append(os.path.dirname(course))  # Name of the course
        module_numbers.append(0)  # We don't have the course ID

        course_path = os.path.join(dir_path, course)
        if not os.path.isdir(course_path):
            continue
        course_categories = os.listdir(course_path)

        categ_node_id = course_node_id
        for category in course_categories:
            count = count + 1
            categ_node_id = categ_node_id + 1

            # Get file name and add it as a node
            file_path = os.path.join(course_path, category)
            file_name = os.path.basename(file_path)
            node_types.append(file_name)

            module_numbers.append(0)  # We don't have the course ID

            # Get file content and add it as a node
            if os.path.exists(file_path):
                with open(file_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
            content_string = json.dumps(data)
            node_texts.append(content_string)

            # Add edges from course to category
            all_edges.append((course_node_id, categ_node_id))
            all_edge_attrs.append(f"Kurs-{file_name}")  # We don't really need an edge attribute

        print(len(node_types))
        print(len(node_texts))
        print(len(module_numbers))
    return all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count


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


def create_node_base_forums(dir_path):
   
    # Listen zur Speicherung der Daten initialisieren
    count = 0
    all_edges = []
    all_edge_attrs = []
    node_texts = []
    node_types = []
    module_numbers = []

    # Alle JSON-Dateien im Verzeichnis durchlaufen und laden
    for filename in os.listdir(dir_path):
        if filename.endswith('.json'):
            file_path = os.path.join(dir_path, filename)
            try:
                with open(file_path, 'r') as file:
                    course_data = json.load(file)
            except json.JSONDecodeError as e:
                print(f"Fehler beim Laden der Datei {filename}: {e}")
                continue
            
            # Knoten und Kanten basierend auf JSON-Daten hinzufügen
            for course in course_data:
                count += 1
                course_node_id = count
                node_types.append("Course")
                node_texts.append(course["Course_Name"])
                module_numbers.append(course["Course_id"])

                if course['Forums']:
                    for forums in course['Forums']:  # Erste Ebene durchlaufen
                        # Sicherstellen, dass forums nicht None ist
                        if forums:
                            for forum in forums:  # Zweite Ebene durchlaufen
                                # Sicherstellen, dass forum nicht None ist
                                if forum:
                                    count += 1
                                    forum_node_id = count
                                    node_types.append("Forum")
                                    node_texts.append(forum['Forum_name'])
                                    module_numbers.append(forum['Forum_id'])

                                    # Add edge from course to forum
                                    all_edges.append((course_node_id, forum_node_id))
                                    all_edge_attrs.append("contains")

                                    discussions = forum.get("Discussions", [])
                                    for discussion in discussions:
                                        count += 1
                                        discussion_node_id = count
                                        node_types.append("Discussion")
                                        node_texts.append(discussion["Discussion_Name"])
                                        module_numbers.append(discussion["Discussion_Id"])

                                        # Add edge from forum to discussion
                                        all_edges.append((forum_node_id, discussion_node_id))
                                        all_edge_attrs.append("contains")

                                        messages = discussion.get("Messages", [])
                                        for message in messages:
                                            count += 1
                                            message_node_id = count
                                            node_types.append("Message")
                                            node_texts.append(message["Content"])
                                            module_numbers.append(message["Message_id"])

                                            # Add edge from discussion to message
                                            all_edges.append((discussion_node_id, message_node_id))
                                            all_edge_attrs.append("contains")

                                            response_to = message.get("Response to")
                                            if response_to and response_to != "Response to nothing" and response_to != "This is the original post":
                                            # Find the node id of the message being responded to
                                                for i, module_number in enumerate(module_numbers):
                                                    if module_number == response_to:
                                                        response_to_node_id = i + 1
                                                        # Add edge for response
                                                        all_edges.append((message_node_id, response_to_node_id))
                                                        all_edge_attrs.append("responds to")
                                                        break

    return all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count