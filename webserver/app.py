from flask import Flask, render_template, jsonify, request, redirect, session
from functools import wraps

from passlib.hash import sha256_crypt

from secret import openai_key

import chromadb
from chromadb.config import Settings

import os

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.vectorstores import Chroma
from langchain.llms import OpenAI

from pymongo import MongoClient

from sentence_transformers import SentenceTransformer

import g4f as g4f
from g4f.Provider import (
    Ails,
    You,
    Bing,
    Yqcloud,
    Theb,
    Aichat,
    Bard,
    Vercel,
    Forefront,
    Lockchat,
    Liaobots,
    H2o,
    ChatgptLogin,
    DeepAi,
    GetGpt
)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

model = SentenceTransformer('distiluse-base-multilingual-cased-v1')

# FOR INSIDE DOCKER
chroma_client = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="chroma",
                                        chroma_server_http_port="8000"
                                ))

chroma_db = Chroma(client=chroma_client, collection_name="data")

chain = load_qa_with_sources_chain(OpenAI(temperature=0), 
                                   chain_type="map_reduce", 
                                   return_intermediate_steps=True)

#FOR INSIDE DOCKER
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
        chat = chats_collection.find_one({'username': session['username']})['chat']

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

@app.post('/logout')
def logout():
    print("new logout")
    data = request.get_json()
    new_history = data["history"]
    print("new history: ", new_history)
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

PROMPT_STRING = "Folgendes ist eine freundliche Unterhaltung zwischen einem Menschen und einer KI die den Namen 'TutorAI' trägt. Die KI ist gesprächig und liefert viele spezifische Details aus ihrem Kontext. Wenn die KI eine Frage nicht beantworten kann, sagt sie ehrlich, dass sie es nicht weiß. Jetzt folgt die Konversation: "

@app.post("/send")
@login_required
def incoming_message():
    data = request.get_json()
    query = data["message"]
    #docs = chroma_db.similarity_search(query, k=5) # TODO
    
    #answer = chain({"input_documents": docs, "question": query}, return_only_outputs=True)
    string=PROMPT_STRING + query # + docs TODO
    response = g4f.ChatCompletion.create(model='gpt-3.5-turbo', provider=DeepAi, messages=[{"role": "user", "content": string}], stream=g4f.Provider.DeepAi.supports_stream)
    return jsonify({"message": ''.join(response).trim("---")})

@app.post("/rate")
@login_required
def rating():
    # TODO
    return jsonify({"message": "Ok."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_evalex=False)