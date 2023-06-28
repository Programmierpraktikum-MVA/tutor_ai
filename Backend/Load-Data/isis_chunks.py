import json
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import DirectoryLoader
from sentence_transformers import SentenceTransformer,util 
from langchain.embeddings import HuggingFaceEmbeddings, SentenceTransformerEmbeddings
import pinecone
model = SentenceTransformer('distiluse-base-multilingual-cased-v1',device='cuda') 



def split_by_thread(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)

    posts = data['messages']
    threads = {}

    for post in posts:
        thread_id = post['link'].split('=')[-1].split('#')[0]
        if thread_id not in threads:
            threads[thread_id] = []
            post['label'] = 'text:'
        else:
            post['label'] = 'antwort:'
        threads[thread_id].append(post)

    thread_chunks = []
    for thread in threads.values():
        chunk = []
        for post in thread:
            chunk.append({'link': post['link'], 'label': post['label'], 'text': post['text']})
        thread_chunks.append(str(chunk)[2:-2])

    return thread_chunks






file_path = 'C:/Users/amorr/Desktop/freegpt/gpt4free/Store/V.json'
thread_chunks = split_by_thread(file_path)

print(thread_chunks[0])


# pinecone.init(api_key="1c4332a1-f46b-41ca-8885-fceca6b66ee5", environment="northamerica-northeast1-gcp")
# index = pinecone.Index("tudata")
# 
# 
# def addData(corpusData,url):
    # id  = index.describe_index_stats()['total_vector_count']
    # for i in range(len(corpusData)):
        # chunk=corpusData[i]
        # chunkInfo=(str(id+i),
                # model.encode(chunk).tolist(),
                # {'title': url,'context': chunk})
        # index.upsert(vectors=[chunkInfo])
        # 
# addData(thread_chunks,"url")
