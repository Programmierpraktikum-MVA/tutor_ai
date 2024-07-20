import torch
import numpy as np
from transformers import BertTokenizer, BertModel
from torch_geometric.data import Data
from torch_geometric.utils import add_remaining_self_loops
from sklearn.metrics.pairwise import cosine_similarity


def intiialize_models():
    tokenizer = BertTokenizer.from_pretrained('bert-base-german-cased')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    bert_model = BertModel.from_pretrained('bert-base-german-cased').to(device)
    return tokenizer, device, bert_model




def get_relevant_embeddings(question_embedding, graph_embeddings, top_k=5):
    """ Gets the top k relevant embeddings from the knowledge graph"""
    # TODO: Test if this works on our graph
    similarities = cosine_similarity(question_embedding.reshape(1, -1), graph_embeddings)
    top_indices = similarities.argsort()[0][-top_k:]
    return top_indices


def question_to_embedding(question, tokenizer, bert_model, device):
    """ Transforms the input question into an embedding for comparison"""
    # TODO: Test if this correctly transfroms the question into an embedding
    inputs = tokenizer(question, return_tensors='pt', truncation=True, padding=True, max_length=512).to(device)
    with torch.no_grad():
        outputs = bert_model(**inputs)
        question_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
    return question_embedding


def embed_to_text(embedding):
    """ Transforms an embedding into text"""
    # Convert the numerical embedding to a string representation
    return ' '.join(map(str, embedding))


def create_combined_input(question, relevant_embeddings):
    """ Combines the input question with the relevant context information from the knowledge graph"""
    # TODO: Test if this works
    embedding_texts = [embed_to_text(emb) for emb in relevant_embeddings]
    combined_text = question + " " + " ".join(embedding_texts)
    return combined_text
