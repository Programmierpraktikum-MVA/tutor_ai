from llama_index.core import (StorageContext, Settings)
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings
)
from llama_index.core.memory import ChatMemoryBuffer
import requests  


llm = Ollama(model="llama3", request_timeout=360.0)
embedding_llm = OllamaEmbedding(model_name="nomic-embed-text")
Settings.llm = llm
Settings.embed_model = embedding_llm
Settings.chunk_size = 512


storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context=storage_context)


memory = ChatMemoryBuffer.from_defaults(token_limit=3900)


def web_search(query):
    response = requests.get(f"https://api.example.com/search?q={query}")
    return response.json()['results']



chat_engine = index.as_chat_engine(
    chat_mode="condense_plus_context",
    memory=memory,
    llm=llm,
    context_prompt=(
        "You are a German chatbot, able to have normal interactions, as well as talk"
        "about modules and informations from the Technische Unvisität Berlin."
        "Here are the relevant documents for the context:\n"
        "{context_str}"
        "\nInstruction: Use the documents, the previous chat history, or the context above, to interact and help the user."
    ),
    verbose=False,
    fallback_handler=web_search  
)



while True:
    user_input = input("User: ")
    if user_input.lower() == "quit":
        break

    response = chat_engine.chat(user_input)
    print ("TutorAi: ")
    print (response)
    
