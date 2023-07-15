# TutorAI Project SoSe 2023

This is the github repo for the TutorAI ODS Programming Project in 2023

The goal of the project is to provide a chatbot for students of the TU Berlin to ask questions about subjects or organizational matters. 

In this year we are using a LLM to generate the final answers and provide supplementary data to the model to improve answers.

The project consists of multiple docker containers that are run using docker compose. To start the project just run `docker compose up --build`. 
This will start the Chroma Vector Database server, the Mongo DB server for user data and the webserver to serve the chat.

# Adding Documents to the Vector Database
First you have to install the chromadb package by running `pip install chromadb`.
Then inside a python file run the following lines to connect to the database and add some documents.
```
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import uuid

chroma_client = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="chroma", # if you are outside of the docker container use localhost
                                        chroma_server_http_port="8000")) # if you are outside of the docker container use 5001

chroma_collection = chroma_client.get_or_create_collection(name="documents", # The collection is called "documents"!
                                                           embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name="distiluse-base-multilingual-cased-v1"))

chroma_collection.add(
    documents=["This is document1", "This is document2"], # we handle tokenization, embedding, and indexing automatically. Replace the strings with the real documents.
    metadatas=[{"source": "notion"}, {"source": "google-docs"}], # Add the metadatas
    ids=[uuid.uuid1(), uuid.uuid1()], # Assign a unique id to each doc. 
)

```

# Useful Documentation
Chroma usage in Langchain: https://python.langchain.com/docs/modules/data_connection/vectorstores/integrations/chroma

Chroma Docs: https://docs.trychroma.com/getting-started