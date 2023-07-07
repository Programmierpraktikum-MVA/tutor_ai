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

app = Flask(__name__)
app.secret_key = 'your_secret_key'

os.environ["OPENAI_API_KEY"] = openai_key

embeddings = OpenAIEmbeddings()

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

@app.post("/send")
@login_required
def incoming_message():
    # TODO
    print("incoming request")
    return jsonify({"message": "Hi Mom."})
    data = request.get_json()
    query = data["message"]
    docs = chroma_db.similarity_search(query, k=5)
    
    answer = chain({"input_documents": docs, "question": query}, return_only_outputs=True)
    return jsonify({"message": answer["output_text"]})

@app.post("/rate")
@login_required
def rating():
    # TODO
    return jsonify({"message": "Ok."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_evalex=False)