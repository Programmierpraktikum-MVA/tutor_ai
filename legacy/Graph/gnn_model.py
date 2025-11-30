import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.utils import add_remaining_self_loops

class GNNModel(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim, bert_dim, num_classes):
        super(GNNModel, self).__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, bert_dim)  # Ensure this matches BERT's output dimension
        self.classifier = torch.nn.Linear(bert_dim, num_classes)  # Separate classifier layer

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        num_nodes = x.size(0)
        print(f"num_nodes: {num_nodes}")  # Debugging-Information
        print(f"edge_index before self-loops: {edge_index.shape}")  # Debugging-Information

        edge_index, _ = add_remaining_self_loops(edge_index, num_nodes=num_nodes)

        print(f"edge_index after self-loops: {edge_index.shape}")  # Debugging-Information
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        embeddings = x  # Store the embeddings before classification
        x = self.classifier(x)
        return embeddings, F.log_softmax(x, dim=1)  # Return both embeddings and log probabilities
