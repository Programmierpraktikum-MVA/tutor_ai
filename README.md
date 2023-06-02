# TutorAI Project SoSe 2023
This is the github repo for the TutorAI ODS Programming Project in 2023

The goal of the project is to provide a chatbot for students of the TU Berlin to ask questions about subjects or organizational matters. 

In this year we are using a LLM to generate the final answers and provide supplementary data to the model to improve answers.

The Frontend is served by a Python Flask Backend. To start the server first create a secret.py that contains your openAI API key, then run `python -m flask run`. The server will he available at `localhost:5000`.

The `add_to_pinecone.py` lets you easily add html documents into the vector DB. I just used it to create a nice demo.
