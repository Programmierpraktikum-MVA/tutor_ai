import os
import spacy
import torch
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from preprocessing import process_transcripts, preprocess_email_data
from graphStuff import create_initial_graph, save_graph, load_graph, create_node_base_sentences, create_node_base_mails, merge_node_base

def initialize_models(device):
    nlp = spacy.load('de_core_news_sm')
    ner_model = pipeline('ner', model='bert-base-german-cased', tokenizer='bert-base-german-cased', device=device.index if torch.cuda.is_available() else -1)
    sentence_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device.index if torch.cuda.is_available() else "cpu")
    return nlp, ner_model, sentence_model

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    nlp, ner_model, sentence_model = initialize_models(device)

    transcripts_folder = 'transcripts'
    sentences = process_transcripts(transcripts_folder, nlp)

    mails_file = 'mail.json'
    mails = preprocess_email_data(mails_file)

    all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent = create_node_base_sentences(sentences)
    all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail = create_node_base_mails(mails)

    all_edges, all_edge_attrs, node_texts, node_types, module_numbers, count = merge_node_base(
        all_edges_sent, all_edge_attrs_sent, node_texts_sent, node_types_sent, module_numbers_sent, count_sent,
        all_edges_mail, all_edge_attrs_mail, node_texts_mail, node_types_mail, module_numbers_mail, count_mail
    )

    graph_data = create_initial_graph(all_edges, all_edge_attrs, node_texts, node_types, module_numbers, device)

    save_graph(graph_data, 'saved_graph.pth')

    loaded_graph_data = load_graph('saved_graph.pth', device)

    print("Finaler Graph:", loaded_graph_data)

if __name__ == "__main__":
    main()
