import os
import spacy
import torch
import json
from transformers import pipeline, BertModel, BertTokenizer
from sentence_transformers import SentenceTransformer
from gnn_model import GNNModel
from preprocessing import preprocess_email_data, process_transcripts
from graphStuff import create_graph, save_graph, load_graph, create_node_base_sentences, create_node_base_mails, merge_node_base

def initialize_models(device):
    nlp = spacy.load('de_core_news_sm')
    ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased', device=device.index if torch.cuda.is_available() else -1)
    sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device.index if torch.cuda.is_available() else "cpu")
    tokenizer = BertTokenizer.from_pretrained('bert-base-german-cased')
    bert_model = BertModel.from_pretrained('bert-base-german-cased').to(device)
    return nlp, ner_model, sentence_model, tokenizer, bert_model

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    nlp, ner_model, sentence_model, tokenizer, bert_model = initialize_models(device)

    transcripts_folder = 'transcripts_json'
    sentences = process_transcripts(transcripts_folder)

    mails_file = 'mail.json'
    mails = preprocess_email_data(mails_file)

    all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent = create_node_base_sentences(sentences)
    all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail = create_node_base_mails(mails)

    #print(all_edges_sent)
    #print(all_edges_mail)

    all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count = merge_node_base(
        all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent,
        all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail
    )
    print("\n\n")
    print(all_edges)
    print("\n\n")
    graph_data = create_graph(all_edges, all_edge_attrs, node_texts, node_types, module_numbers, tokenizer, bert_model, device).to(device)
    save_graph(graph_data, 'saved_graph.pth')

    loaded_graph_data = load_graph('saved_graph.pth', device)

    print(f"Finaler Graph: {loaded_graph_data}")  # Debugging-Information
    print(f"edge_index shape after loading: {loaded_graph_data.edge_index.shape}")  # Debugging-Information
    print(f"edge_index values after loading: {loaded_graph_data.edge_index}")  # Debugging-Information

    # GNN Training
    model = GNNModel(input_dim=loaded_graph_data.x.size(1), hidden_dim=128, output_dim=64, num_classes=len(loaded_graph_data.type_to_index)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    model.train()

    type_indices = torch.tensor([loaded_graph_data.type_to_index[type_] for type_ in loaded_graph_data.node_types], dtype=torch.long).to(device)

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
    for i, (embedding, node_text, node_type, module_number) in enumerate(zip(embeddings, loaded_graph_data.node_texts, loaded_graph_data.node_types, loaded_graph_data.module_numbers)):
        node_data.append({
            'node_index': i,
            'embedding': embedding.tolist(),
            'text': node_text,
            'type': node_type,
            'module_number': module_number
        })

    # Speichern der Node-Daten in einer JSON-Datei
    with open('node_data.json', 'w') as f:
        json.dump(node_data, f)

    print("Node Embeddings and attributes saved to node_data.json")

if __name__ == "__main__":
    main()
