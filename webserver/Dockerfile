FROM python:3.11.4-slim

#COPY requirements.txt .

RUN python -m venv venv
RUN . venv/bin/activate

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install flask chromadb-client langchain pymongo openai passlib

WORKDIR /app

COPY . .

CMD ["python",  "app.py"]