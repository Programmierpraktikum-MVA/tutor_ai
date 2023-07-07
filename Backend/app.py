"This code uses the g4f Module"


import g4f
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


import streamlit as st 
import prompt_engineering as pe
import g4f
import pinecone
from sentence_transformers import SentenceTransformer,util 
from flask import Flask, render_template, request, jsonify
model = SentenceTransformer('distiluse-base-multilingual-cased-v1',device='cuda') 


app = Flask(__name__, static_url_path='/static')

@app.route("/")
def index():
    return render_template('chat.html')


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    return get_Chat_response(input)


def get_Chat_response(text):
    "replace this part with your model"
    def find_match(query,k):
        query_em = model.encode(query).tolist()
        result = index.query(query_em, top_k=k, includeMetadata=True)
        return [result['matches'][i]['metadata']['title'] for i in range(k)],[result['matches'][i]['metadata']['context'] for i in range(k)]
    
    pinecone.init(api_key="1c4332a1-f46b-41ca-8885-fceca6b66ee5", environment="northamerica-northeast1-gcp")
    index = pinecone.Index("tudata")
    transformer = str(find_match(text,1))
    prompt = pe.structured_input(text,transformer)
    response = g4f.ChatCompletion.create(model='gpt-3.5-turbo', provider=DeepAi,
                messages=[{"role": "user", "content": prompt}], stream=g4f.Provider.DeepAi.supports_stream)
    return response


if __name__ == '__main__':
    app.run()