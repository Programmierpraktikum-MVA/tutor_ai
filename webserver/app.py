from flask import Flask, render_template, jsonify, request, redirect, session
from functools import wraps

from passlib.hash import sha256_crypt

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from pymongo import MongoClient

import g4f as g4f
from g4f.Provider import DeepAi

import os
import json


import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'


def split_json_files(folder_path, max_chunk_length=2000):
    chunks = []
    meta = []
    id = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.endswith('.json'):
            with open(file_path, 'r') as file:
                data = json.load(file)
                title = data.get('Titel des Moduls', '')
                json_str = json.dumps(data)
                k = 0
                for i in range(0, len(json_str), max_chunk_length):
                    chunk = title + json_str[i:i+max_chunk_length]
                    chunks.append(chunk)
                    meta.append({"title": title, "filename": filename})
                    id.append("moses-id_"+filename+"_"+str(k))
                    k += 1
                    
    return chunks,meta,id



def split_by_thread(folder_path):
    thread_chunks = []
    id = []
    meta=[]
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path,filename)
        print(str(file_path))
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

        
        for k, thread in enumerate(threads.values()):
            chunk = []
            for post in thread:
                chunk.append({'link': post['link'], 'label': post['label'], 'text': post['text']})
            thread_chunks.append(str(chunk)[2:-2])
            id.append("isis-id_"+filename+"_"+str(k))
            meta.append({"filename": filename})
        
    return thread_chunks,id,meta



#folder_path = './moses'
#chunk_list,meta,id = split_json_files(folder_path)


file_path = './isis'
thread_chunks,id,meta = split_by_thread(file_path)

# Chroma DB for document storage
chroma_client = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="chroma",
                                        chroma_server_http_port="8000"))

print(chroma_client.list_collections())

chroma_collection = chroma_client.get_or_create_collection(name="documents", 
                                                           embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name="distiluse-base-multilingual-cased-v1"))



# chroma_collection.add(
    # documents=thread_chunks, # we handle tokenization, embedding, and indexing automatically. Replace the strings with the real documents.
    # metadatas=meta, # Add the metadatas
    # ids=id, # Assign a unique id to each doc. 
# )

print(chroma_collection.count())

# MONGO DB for User Data and Chat History
CONNECTION_STRING = "mongodb://root:example@mongo"

mongo_client = MongoClient(CONNECTION_STRING)
mongo_db = mongo_client['tutorai']
users_collection = mongo_db['users']
chats_collection = mongo_db['chats']

def login_required(route_function):
    @wraps(route_function)
    def decorated_route(*args, **kwargs):
        if 'username' not in session:
            return redirect('/login')
        return route_function(*args, **kwargs)
    return decorated_route

@app.route("/")
@login_required
def home():
    if 'username' in session:
        try:
            chat = chats_collection.find_one({'username': session['username']})['chat']
        except:
            return redirect('/login')

        return render_template('chat.html', username=session['username'], chat=chat)
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users_collection.find_one({'username': username})

        # Validate the username and password (you may check against a database)
        if user and sha256_crypt.verify(password, user['password']):
            session['username'] = username
            return redirect('/')
        else:
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    if request.method == "POST":
        data = request.get_json()
        new_history = data["history"]
        chats_collection.update_one({'username': session['username']}, {'$push': {'chat': { '$each': new_history }}})
        session.pop('username', None)
        
    return redirect('/login') 

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = sha256_crypt.hash(password)

        # Store the username and hashed password in the database
        users_collection.insert_one({'username': username, 'password': hashed_password})
        chats_collection.insert_one({'username': username, 'chat': []})

        return redirect('/login')

    return render_template('register.html')

prompt = "Du bist TutorAI eine KI die darauf spezialisiert war als persönlicher Tutor der technischen Universität zu dienen."

@app.post("/send")
@login_required
def incoming_message():
    data = request.get_json()
    query = data["message"]
    
    words = query.split('---')
    last_word = words[-1].strip()
    docs = chroma_collection.query(query_texts=[last_word], n_results=2)
    
    
    docs = " --- ".join(docs['documents'][0])
    #Die Daten müssen von der Vektor-Datenbank gelöscht werden. Momentan sind noch Testdaten enthalten.
    
    string = prompt+query
    

    response = g4f.ChatCompletion.create(model='gpt-3.5-turbo', provider=DeepAi, messages=[{"role": "user", "content": string}], stream=g4f.Provider.DeepAi.supports_stream)
    return jsonify({"message": ''.join(response).strip("---")})
    # return jsonify({"message": str(docs)})

@app.post("/rate")
@login_required
def rating():
    # TODO
    return jsonify({"message": "Ok."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_evalex=False)
