from flask import Flask, render_template, jsonify, request, redirect, session, flash
from functools import wraps
from passlib.hash import sha256_crypt
from pymongo import MongoClient
import ratings

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
    string = PROMPT_STRING + "\nJetzt die bisherige Konversation: \n" + query + "\nDie KI antwortet auf diese Konversation folgendermaßen: "
    response = "dummy response"
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
