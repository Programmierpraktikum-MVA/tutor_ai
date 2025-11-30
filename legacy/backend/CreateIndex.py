from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings,
    TreeIndex
)



llm = Ollama(model="llama3", request_timeout=360.0)
embedding_llm = OllamaEmbedding(model_name="nomic-embed-text")

Settings.llm = llm
Settings.embed_model = embedding_llm
Settings.chunk_size = 1024

# There is a folder called data in which you have to put your documents
documents = SimpleDirectoryReader("data", recursive=True).load_data()



index = VectorStoreIndex.from_documents(documents)


query_engine = index.as_query_engine(
    include_text=True,
    response_mode="tree_summarize",
    embedding_mode="hybrid",
    similarity_top_k=5,
)

# persist the index to use it in the chat engine
index.storage_context.persist()

