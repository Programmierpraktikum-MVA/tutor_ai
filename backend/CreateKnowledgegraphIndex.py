from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    load_index_from_storage,
    Settings,
    KnowledgeGraphIndex,

)

from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.core import StorageContext



# Replace 'data5' with the actual file where your documents are located
documents = SimpleDirectoryReader("data", recursive=True).load_data()


llm = Ollama(model="llama3", request_timeout=360.0)
embedding_llm = OllamaEmbedding(model_name="nomic-embed-text")


Settings.llm = llm
Settings.embed_model = embedding_llm
Settings.chunk_size = 1024
Settings.chunk_overlap = 100


graph_store = SimpleGraphStore()


storage_context = StorageContext.from_defaults(graph_store=graph_store)

index = KnowledgeGraphIndex.from_documents(
    documents,
    storage_context=storage_context,
    max_triplets_per_chunk=5,
    include_embeddings=True,
)








index.storage_context.persist()



    
    


