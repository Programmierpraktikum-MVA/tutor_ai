
import os
os.environ["OPENAI_API_KEY"] = "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"
import pinecone
pinecone.init(api_key="9e2970aa-e27c-4911-8fae-e4fe07a9af27", environment="asia-southeast1-gcp-free")
from tqdm.auto import tqdm
from uuid import uuid4
import grpc
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Pinecone
from langchain.document_loaders import HuggingFaceDatasetLoader
from langchain.prompts import PromptTemplate
from datasets import load_dataset
from getpass import getpass
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
import tiktoken
tiktoken.encoding_for_model('gpt-3.5-turbo')

data = load_dataset("wikipedia", "20220301.simple", split='train[:10000]')


tokenizer = tiktoken.get_encoding('cl100k_base')

# create the length function
def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

tiktoken_len("hello I am a chunk of text and using the tiktoken_len function "
             "we can find the length of this chunk of text in tokens")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=20,
    length_function=tiktoken_len,
    separators=["\n\n", "\n", " ", ""]
)

chunks = text_splitter.split_text(data[6]['text'])[:3]

tiktoken_len(chunks[0]), tiktoken_len(chunks[1]), tiktoken_len(chunks[2])

model_name = 'text-embedding-ada-002'

embed = OpenAIEmbeddings(
    model=model_name,
    openai_api_key="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"
)

texts = [
    'this is the first chunk of text',
    'then another second chunk of text is here'
]

res = embed.embed_documents(texts)
len(res), len(res[0])

index_name = 'langchain-retrieval-augmentation'
pinecone.init(
    api_key="9e2970aa-e27c-4911-8fae-e4fe07a9af27",
    environment="asia-southeast1-gcp-free"
)

if index_name not in pinecone.list_indexes():
    # we create a new index
    pinecone.create_index(
        name=index_name,
        metric='dotproduct',
        dimension=len(res[0])  # 1536 dim of text-embedding-ada-002
    )

""" index = pinecone.Index(index_name)

index.describe_index_stats()
 """

""" batch_limit = 100

texts = []
metadatas = []
 """
""" for i, record in enumerate(tqdm(data)):
    # first get metadata fields for this record
    metadata = {
        'wiki-id': str(record['id']),
        'source': record['url'],
        'title': record['title']
    }
    # now we create chunks from the record text
    record_texts = text_splitter.split_text(record['text'])
    # create individual metadata dicts for each chunk
    record_metadatas = [{
        "chunk": j, "text": text, **metadata
    } for j, text in enumerate(record_texts)]
    # append these to current batches
    texts.extend(record_texts)
    metadatas.extend(record_metadatas)
    # if we have reached the batch_limit we can add texts
    if len(texts) >= batch_limit:
        ids = [str(uuid4()) for _ in range(len(texts))]
        embeds = embed.embed_documents(texts)
        index.upsert(vectors=zip(ids, embeds, metadatas))
        texts = []
        metadatas = [] """

""" if len(texts) > 0:
    ids = [str(uuid4()) for _ in range(len(texts))]
    embeds = embed.embed_documents(texts)
    index.upsert(vectors=zip(ids, embeds, metadatas)) """

""" index.describe_index_stats() """

text_field = "text"

# switch back to normal index for langchain
index = pinecone.Index(index_name)

vectorstore = Pinecone(
    index, embed.embed_query, text_field
)

query = "who was Stalin?"

vectorstore.similarity_search(
    query,  # our search query
    k=3  # return 3 most relevant docs
)

# completion llm
llm = ChatOpenAI(
    openai_api_key="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",
    model_name='gpt-3.5-turbo',
    temperature=0.0
)

qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever()
)

qa.run(query)
print(qa.run(query))



qa_with_sources = RetrievalQAWithSourcesChain.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever()
)

print(qa_with_sources(query))

