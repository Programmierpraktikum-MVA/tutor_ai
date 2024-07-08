from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get("question")
    # Hier kannst du die Antwort des LLM simulieren
    response = {
        "answer": f"Das ist eine simulierte Antwort auf: '{question}'"
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=5000)
