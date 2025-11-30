# Note: I am mostly following the demo from the github repository of LLama-parse that can be found here: https://github.com/run-llama/llama_parse/blob/main/examples/demo_advanced.ipynb

import nest_asyncio
import os
from llama_parse import LlamaParse
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter, SimpleNodeParser

from unstructured.partition.auto import partition

# pip install unstructured[pdf]
# elements = partition("Blatt01_Sol_Tut.pdf")
#
# print("\nBREAAAAAAAAAAAAAK\n".join([str(el) for el in elements]))
# print("done")

print(os.getcwd())

reader = SimpleDirectoryReader(input_dir="pdf_folder")
docs = reader.load_data()

node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)

nodes = node_parser.get_nodes_from_documents(
    docs, show_progress=False
)

for node in nodes:
    print(node)

    print("BREAK \n")

# os.environ["LLAMA_CLOUD_API_KEY"] = "llx-Hpwjm4LZR0Xz4FV9By6qemty9ZoekaSh4UbW51Jpni4yO6tp"
# documents = LlamaParse(result_type="markdown").load_data("./Blatt01_Sol_Tut.pdf")

# loader = SimpleDirectoryReader(
#             input_dir = "./",
#             required_exts=[".pdf"],
#             recursive=True
#         )
# docs = loader.load_data()
#
# splitter = SentenceSplitter(
#     chunk_size = 100,
#     chunk_overlap = 15,
# )
# nodes = splitter.get_nodes_from_documents(docs)
#
# print(nodes[0])
#
# for node in nodes:
#     print(node)
#     print("--------------------\n")


# This is a long document we can split up.
