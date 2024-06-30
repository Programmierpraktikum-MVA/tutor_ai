from flask import Flask, render_template, jsonify, request, redirect, session, flash
from functools import wraps
from passlib.hash import sha256_crypt
from pymongo import MongoClient
import ratings

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
from llama_index.core.storage.chat_store import SimpleChatStore

llm = Ollama(model="llama3", request_timeout=360.0)
embedding_llm = OllamaEmbedding(model_name="nomic-embed-text")
Settings.llm = llm
Settings.embed_model = embedding_llm
Settings.chunk_size = 512


storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context=storage_context)


chat_store = SimpleChatStore()
memory = ChatMemoryBuffer.from_defaults(
    token_limit=20000,
    chat_store=chat_store,
    chat_store_key="user1",)

chat_store.persist(persist_path="chat_store.json")
loaded_chat_store = SimpleChatStore.from_persist_path(
    persist_path="chat_store.json"
)

def web_search(query):
    response = requests.get(f"https://api.example.com/search?q={query}")
    return response.json()['results']


chat_engine = index.as_chat_engine(
    chat_mode="condense_plus_context",
    memory=memory,
    llm=llm,
    context_prompt=(
        "Answer only in German"
        "You are a German chatbot, able to have normal interactions, as well as talk"
        "about modules, technical information about the modules, and informations from the Technical University of Berlin."
        "Here are the relevant documents for the context:\n"
        "{context_str}"
        "\nInstruction: Use the previous chat history, or the context above, to interact and help the user."
    ),
    verbose=False,
    fallback_handler=web_search,
)



app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MONGO DB for User Data and Chat History
CONNECTION_STRING = "mongodb://localhost:27017"

mongo_client = MongoClient(CONNECTION_STRING)
mongo_db = mongo_client['tutorai']
users_collection = mongo_db['users']
chats_collection = mongo_db['chats']

def login_required(route_function):
    @wraps(route_function)
    def decorated_route(*args, **kwargs):
        if 'username' not in session:
            flash('Please login first', 'warning')
            return redirect('/login')
        return route_function(*args, **kwargs)
    return decorated_route

@app.route("/")
@login_required
def home():
    chat = chats_collection.find_one({'username': session['username']})['chat']
    return render_template('chat.html', username=session['username'], chat=chat)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users_collection.find_one({'username': username})

        if user and sha256_crypt.verify(password, user['password']):
            session['username'] = user['username']
            flash('Login successful!', 'login_success')
            return redirect('/')
        else:
            flash('Invalid credentials, please try again.', 'login_danger')

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    if request.method == "POST":
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect('/login')
    
    return redirect('login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = sha256_crypt.hash(password)

        if users_collection.find_one({'username': username}):
            flash('Username already exists, please choose another one.', 'register_warning')
        else:
            users_collection.insert_one({'username': username, 'password': hashed_password})
            chats_collection.insert_one({'username': username, 'chat': []})
            flash('Registration successful! Please login.', 'register_success')
            return redirect('/login')

    return render_template('register.html')

PROMPT_STRING = """
Folgendes ist eine freundliche Unterhaltung zwischen einem Menschen und einer KI die den Namen 'TutorAI' trägt. 
Die KI ist gesprächig und liefert viele spezifische Details aus ihrem Kontext. 
Wenn die KI eine Frage nicht beantworten kann, sagt sie ehrlich, dass sie es nicht weiß. 
"""

@app.post("/send")
@login_required
def incoming_message():
    data = request.get_json()
    query = data["message"]
    
    response = chat_engine.stream_chat(query)
    response_return = ""
    for token in response.response_gen:
        response_return += token + ""
    return jsonify({"message": response_return})

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
