import os
import spacy
import torch
import json
from transformers import pipeline, BertModel, BertTokenizer
from sentence_transformers import SentenceTransformer
from gnn_model import GNNModel
from preprocessing import preprocess_email_data, process_transcripts
from graphStuff import create_graph, save_graph, load_graph, create_node_base_sentences, create_node_base_mails, \
    merge_node_base, create_node_base_sentences_cosine_avail, create_node_base_moses, create_node_base_forums
from save_functions import save_edges, save_edge_attrs, save_node_texts, save_node_types, save_module_numbers


def initialize_models(device):
    nlp = spacy.load('de_core_news_sm')
    ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased',
                         device=device.index if torch.cuda.is_available() else -1)
    sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2',
                                         device=device.index if torch.cuda.is_available() else "cpu")
    tokenizer = BertTokenizer.from_pretrained('bert-base-german-cased')
    bert_model = BertModel.from_pretrained('bert-base-german-cased').to(device)
    return nlp, ner_model, sentence_model, tokenizer, bert_model

def main_moses():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    dir_path = "/home/tomklein/Documents/uni/tutorAI/course_id_data/CourseInfosMosesDemo"
    nlp, ner_model, sentence_model, tokenizer, bert_model = initialize_models(device)
    all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count = create_node_base_moses(dir_path)

    save_edges(all_edges)
    print("ecken gespeichert")
    save_edge_attrs(all_edge_attrs)
    print("ecken attr gespeichert")
    save_node_texts(node_texts)
    print("node text gespeichert")
    save_node_types(node_types)
    print("node types gespeichert")
    save_module_numbers(module_numbers)
    print("module numbers gespeichert")

    graph_data = create_graph(all_edges, all_edge_attrs, node_texts, node_types, module_numbers, tokenizer, bert_model,
                              device).to(device)
    print("Graph erstellt")
    save_graph(graph_data, 'saved_graph.pth')
    print("Graph gespeichert")

    loaded_graph_data = load_graph('saved_graph.pth', device)

    print(f"Finaler Graph: {loaded_graph_data}")  # Debugging-Information
    print(f"edge_index shape after loading: {loaded_graph_data.edge_index.shape}")  # Debugging-Information
    print(f"edge_index values after loading: {loaded_graph_data.edge_index}")  # Debugging-Information

    # GNN Training
    model = GNNModel(input_dim=loaded_graph_data.x.size(1), hidden_dim=128, output_dim=64,
                     num_classes=len(loaded_graph_data.type_to_index)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    model.train()

    type_indices = torch.tensor([loaded_graph_data.type_to_index[type_] for type_ in loaded_graph_data.node_types],
                                dtype=torch.long).to(device)

    for epoch in range(200):
        optimizer.zero_grad()
        out, log_probs = model(loaded_graph_data)
        print(f"Shape of edge_index: {loaded_graph_data.edge_index.shape}")  # Debugging-Information
        print(f"edge_index values during training: {loaded_graph_data.edge_index}")  # Debugging-Information
        loss = torch.nn.functional.nll_loss(log_probs, type_indices)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f'Epoch {epoch}, Loss: {loss.item()}')

    model.eval()
    with torch.no_grad():
        embeddings, _ = model(loaded_graph_data)

    # Konvertieren der Embeddings und der zugehörigen Informationen in ein für LlamaIndex geeignetes Format
    embeddings = embeddings.cpu().numpy()
    node_data = []
    for i, (embedding, node_text, node_type, module_number) in enumerate(
            zip(embeddings, loaded_graph_data.node_texts, loaded_graph_data.node_types,
                loaded_graph_data.module_numbers)):
        node_data.append({
            'node_index': i,
            'embedding': embedding.tolist(),
            'text': node_text,
            'type': node_type,
            'module_number': module_number
        })

    # Speichern der Node-Daten in einer JSON-Datei
    with open('node_data.json', 'w') as f:
        json.dump(node_data, f, indent=4)

    print("Node Embeddings and attributes saved to node_data.json")

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    nlp, ner_model, sentence_model, tokenizer, bert_model = initialize_models(device)

    transcripts_folder = 'transcripts_json'
    sentences = process_transcripts(transcripts_folder)

    mails_file = 'mail.json'
    mails = preprocess_email_data(mails_file)

    all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent = create_node_base_sentences(
        sentences)
    all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail = create_node_base_mails(
        mails)

    print("merge jetzt alle nodes")


    all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count = merge_node_base(
        all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent,
        all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail
    )

    print("alle nodes merged")

    save_edges(all_edges)
    print("ecken gespeichert")
    save_edge_attrs(all_edge_attrs)
    print("ecken attr gespeichert")
    save_node_texts(node_texts)
    print("node text gespeichert")
    save_node_types(node_types)
    print("node types gespeichert")
    save_module_numbers(module_numbers)
    print("module numbers gespeichert")

    graph_data = create_graph(all_edges, all_edge_attrs, node_texts, node_types, module_numbers, tokenizer, bert_model,
                              device).to(device)
    print("Graph erstellt")
    save_graph(graph_data, 'saved_graph.pth')
    print("Graph gespeichert")

    loaded_graph_data = load_graph('saved_graph.pth', device)

    print(f"Finaler Graph: {loaded_graph_data}")  # Debugging-Information
    print(f"edge_index shape after loading: {loaded_graph_data.edge_index.shape}")  # Debugging-Information
    print(f"edge_index values after loading: {loaded_graph_data.edge_index}")  # Debugging-Information

    # GNN Training
    model = GNNModel(input_dim=loaded_graph_data.x.size(1), hidden_dim=128, output_dim=64,
                     num_classes=len(loaded_graph_data.type_to_index)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    model.train()

    type_indices = torch.tensor([loaded_graph_data.type_to_index[type_] for type_ in loaded_graph_data.node_types],
                                dtype=torch.long).to(device)

    for epoch in range(200):
        optimizer.zero_grad()
        out, log_probs = model(loaded_graph_data)
        print(f"Shape of edge_index: {loaded_graph_data.edge_index.shape}")  # Debugging-Information
        print(f"edge_index values during training: {loaded_graph_data.edge_index}")  # Debugging-Information
        loss = torch.nn.functional.nll_loss(log_probs, type_indices)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f'Epoch {epoch}, Loss: {loss.item()}')

    model.eval()







    with torch.no_grad():
        embeddings, _ = model(loaded_graph_data)
    # Konvertieren der Embeddings und der zugehörigen Informationen in ein für LlamaIndex geeignetes Format
    embeddings = embeddings.cpu().numpy()
    node_data = []
    for i, (embedding, node_text, node_type, module_number) in enumerate(
            zip(embeddings, loaded_graph_data.node_texts, loaded_graph_data.node_types,
                loaded_graph_data.module_numbers)):
        node_data.append({
            'node_index': i,
            'embedding': embedding.tolist(),
            'text': node_text,
            'type': node_type,
            'module_number': module_number
        })

    # Speichern der Node-Daten in einer JSON-Datei
    with open('node_data.json', 'w') as f:
        json.dump(node_data, f, indent=4)

    print("Node Embeddings and attributes saved to node_data.json")


def main_two():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    nlp, ner_model, sentence_model, tokenizer, bert_model = initialize_models(device)

    print("start process transcripts")

    transcripts_folder = 'transcripts_json'
    sentences = process_transcripts(transcripts_folder)

    mails_file = 'mail.json'
    mails = preprocess_email_data(mails_file)

    print("start create node base sentences cosine avail")

    all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent = create_node_base_sentences(
        sentences)
    print("start mail stuff")
    all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail = create_node_base_mails(
        mails)
    all_edges_forum, all_edge_attrs_forum, node_texts_forum, node_types_forum, module_numbers_forum, count_forum = create_node_base_forums('course_forum_data')
    all_edges_moses, all_edge_attrs_moses, node_texts_moses, node_types_moses, module_numbers_moses, count_moses = create_node_base_moses('CourseInfosMoses')

    print("merge hier sent and mail")
    all_edges_temp1, all_edge_attrs_temp1, node_texts_temp1, node_types_temp1, module_numbers_temp1, count_temp1 = merge_node_base(
        all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent,
        all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail
    )
    print("merge hier forum and moses")
    all_edges_temp2, all_edge_attrs_temp2, node_texts_temp2, node_types_temp2, module_numbers_temp2, count_temp2 = merge_node_base(
        all_edges_forum, all_edge_attrs_forum, node_texts_forum, node_types_forum, module_numbers_forum, count_forum,
        all_edges_moses, all_edge_attrs_moses, node_texts_moses, node_types_moses, module_numbers_moses, count_moses
    )

    print("merge hier temp1 and temp2")
    all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count = merge_node_base(
        all_edges_temp1, all_edge_attrs_temp1, node_texts_temp1, node_types_temp1, module_numbers_temp1, count_temp1,
        all_edges_temp2, all_edge_attrs_temp2, node_texts_temp2, node_types_temp2, module_numbers_temp2, count_temp2
    )




    print("save die edges")
    save_edges(all_edges)
    print("save die edges_attr")
    save_edge_attrs(all_edge_attrs)
    print("save die node_texts")
    save_node_texts(node_texts)
    print("save die node_types")
    save_node_types(node_types)
    print("save die module_numbers")
    save_module_numbers(module_numbers)

    print("create_graph")
    graph_data = create_graph(all_edges, all_edge_attrs, node_texts, node_types, module_numbers, tokenizer, bert_model,
                              device).to(device)
    print("save graph data")
    save_graph(graph_data, 'saved_graph.pth')
    print("load graph data")
    loaded_graph_data = load_graph('saved_graph.pth', device)

    print(f"Finaler Graph: {loaded_graph_data}")  # Debugging-Information
    print(f"edge_index shape after loading: {loaded_graph_data.edge_index.shape}")  # Debugging-Information
    print(f"edge_index values after loading: {loaded_graph_data.edge_index}")  # Debugging-Information

    # GNN Training
    model = GNNModel(input_dim=loaded_graph_data.x.size(1), hidden_dim=128, output_dim=64,
                     num_classes=len(loaded_graph_data.type_to_index)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    model.train()

    type_indices = torch.tensor([loaded_graph_data.type_to_index[type_] for type_ in loaded_graph_data.node_types],
                                dtype=torch.long).to(device)

    for epoch in range(200):
        optimizer.zero_grad()
        out, log_probs = model(loaded_graph_data)
        print(f"Shape of edge_index: {loaded_graph_data.edge_index.shape}")  # Debugging-Information
        print(f"edge_index values during training: {loaded_graph_data.edge_index}")  # Debugging-Information
        loss = torch.nn.functional.nll_loss(log_probs, type_indices)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f'Epoch {epoch}, Loss: {loss.item()}')

    model.eval()
    with torch.no_grad():
        embeddings, _ = model(loaded_graph_data)

    # Konvertieren der Embeddings und der zugehörigen Informationen in ein für LlamaIndex geeignetes Format
    embeddings = embeddings.cpu().numpy()
    node_data = []
    for i, (embedding, node_text, node_type, module_number) in enumerate(
            zip(embeddings, loaded_graph_data.node_texts, loaded_graph_data.node_types,
                loaded_graph_data.module_numbers)):
        node_data.append({
            'node_index': i,
            'embedding': embedding.tolist(),
            'text': node_text,
            'type': node_type,
            'module_number': module_number
        })

    # Speichern der Node-Daten in einer JSON-Datei
    with open('node_data.json', 'w') as f:
        json.dump(node_data, f, indent=4)

    print("Node Embeddings and attributes saved to node_data.json")



if __name__ == "__main__":
    main_two()