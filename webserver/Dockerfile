FROM python:3.11.4-slim

#COPY requirements.txt .

RUN python -m venv venv
RUN . venv/bin/activate

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install flask chromadb-client langchain pymongo openai passlib sentence-transformer

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD ["python",  "app.py"]