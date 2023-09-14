from flask import Flask, render_template, jsonify, request, redirect, session
from functools import wraps

from passlib.hash import sha256_crypt

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from pymongo import MongoClient

import g4f as g4f
#from g4f.Provider import OpenaiChat

import ratings

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Chroma DB for document storage
chroma_client = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="chroma",
                                        chroma_server_http_port="8000"))

print(chroma_client.list_collections())

chroma_collection = chroma_client.get_or_create_collection(name="documents", 
                                                           embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2"))

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

PROMPT_STRING = """
Folgendes ist eine freundliche Unterhaltung zwischen einem Menschen und einer KI die den Namen 'TutorAI' trägt. 
Die KI ist gesprächig und liefert viele spezifische Details aus ihrem Kontext. 
Wenn die KI eine Frage nicht beantworten kann, sagt sie ehrlich, dass sie es nicht weiß. 
Zuerst siehst du nützliche zusätzliche Informationen aus Dokumenten, welche dir bei der Antwort dienen werden. 
Dann siehst du den Verlauf der bisherigen Unterhaltung um den Kontext zu verstehen.
Hier also zuerst die Dokumente: 
"""

@app.post("/send")
@login_required
def incoming_message():
    data = request.get_json()
    query = data["message"]
    docs = chroma_collection.query( query_texts=[query], n_results=5)
    docs = " --- ".join(docs['documents'][0])
    string = PROMPT_STRING + docs + "\nJetzt die bisherige Konversation: \n" + query + "\nDie KI antwortet auf diese Konversation folgendermaßen: "
    response = g4f.ChatCompletion.create(model='gpt-3.5-turbo',provider=g4f.Provider.Aichat, messages=[{"role": "user", "content": string}])
    return jsonify({"message": ''.join(response)})

@app.post("/rate")
@login_required
def rating():
    data = request.get_json()
    bot_message = data["bot"]["message"]
    user_message = data["user"]["message"]
    rating = int(data["rating"])
    rating_tuple = (rating, user_message, bot_message)
    
    
    ratings.insert_rating(rating_tuple)
    

    return jsonify({"status": "Ok."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, use_evalex=False)
