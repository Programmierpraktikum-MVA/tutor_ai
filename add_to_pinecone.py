from secret import openai_key, pinecone_key, pinecone_server
import pinecone
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.llms import OpenAI
import os

os.environ["OPENAI_API_KEY"] = openai_key

pinecone.init(
    api_key=pinecone_key,  # find at app.pinecone.io
    environment=pinecone_server  # next to api key in console
)

loader = DirectoryLoader('./html_data')
documents = loader.load()
assert len(documents) != 0
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = text_splitter.split_documents(documents)
print(docs[0])
embeddings = OpenAIEmbeddings()

docsearch = Pinecone.from_documents(docs, embeddings, index_name="tutorai")