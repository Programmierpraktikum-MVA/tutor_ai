from flask import Flask, render_template, jsonify, request
from secret import openai_key, pinecone_key, pinecone_server
import pinecone
import os
from langchain.document_loaders import UnstructuredURLLoader, DirectoryLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.vectorstores import Pinecone
from langchain.llms import OpenAI

app = Flask(__name__)

os.environ["OPENAI_API_KEY"] = openai_key

embeddings = OpenAIEmbeddings()

pinecone.init(
    api_key=pinecone_key,  # find at app.pinecone.io
    environment=pinecone_server  # next to api key in console
)

index = Pinecone.from_existing_index("tutorai", embeddings)
chain = load_qa_with_sources_chain(OpenAI(temperature=0), chain_type="map_reduce", return_intermediate_steps=True)
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=20)

@app.route("/")
def chat():
    return render_template('new_chat.html')

@app.post("/send")
def incoming_message():
    data = request.get_json()
    query = data["message"]
    print("New question: ", query)
    docs = index.similarity_search(query, k=5)
    
    answer = chain({"input_documents": docs, "question": query}, return_only_outputs=True)
    print(answer)
    return jsonify({"message": answer["output_text"]})
