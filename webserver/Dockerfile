FROM python:3.11.4

#COPY requirements.txt .

RUN python -m venv venv
RUN . venv/bin/activate

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install flask pymongo passlib chromadb==0.3.26 sentence_transformers

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install "pydantic==1.*"

WORKDIR /app

COPY . .

CMD ["python",  "app.py"]
