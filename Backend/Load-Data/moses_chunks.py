import json
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import DirectoryLoader
from sentence_transformers import SentenceTransformer,util 
from langchain.embeddings import HuggingFaceEmbeddings, SentenceTransformerEmbeddings
import pinecone
import json
import os

model = SentenceTransformer('distiluse-base-multilingual-cased-v1',device='cuda') 

# Specify the directory path where your JSON files are located
directory_path = 'C:/Users/amorr/Desktop/freegpt/gpt4free/moses'

# Initialize an empty list to store the contents of each file
file_contents = []

# Iterate over each file in the directory
for filename in os.listdir(directory_path):
    if filename.endswith('.json'):
        file_path = os.path.join(directory_path, filename)
        
        # Open the file and load its contents as a dictionary
        with open(file_path, 'r') as file:
            json_data = json.load(file)
            
            # Convert the dictionary to a JSON string
            json_string = json.dumps(json_data)
            
            # Append the JSON string to the list
            file_contents.append(json_string)

# Print the list of file contents
#print(file_contents)


pinecone.init(api_key="1c4332a1-f46b-41ca-8885-fceca6b66ee5", environment="northamerica-northeast1-gcp")
index = pinecone.Index("tudata")


def addData(corpusData,url):
    id  = index.describe_index_stats()['total_vector_count']
    for i in range(len(corpusData)):
        chunk=corpusData[i]
        chunkInfo=(str(id+i),
                model.encode(chunk).tolist(),
                {'title': url,'context': chunk})
        index.upsert(vectors=[chunkInfo])
        
addData(file_contents,"url")
