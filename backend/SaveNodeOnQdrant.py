import json
import qdrant_client
from qdrant_client.models import PointStruct,VectorParams,Distance


# Qdrant-Client initialisieren
client = qdrant_client.QdrantClient(
    url="https://dc2b94d5-016b-44b1-b0f9-ffa4a0eb211b.us-east4-0.gcp.cloud.qdrant.io:6333",
    api_key="gSKCVGZ_4-ze0RTbtJxluOU3M_ZdtbVriRWCQTQRkbkYYSL00ed05g",
    )



# Sammlung erstellen (falls nicht bereits erstellt)
client.create_collection(
    collection_name='knowledge_graph',
    vectors_config={
        "": VectorParams(
            size=6,  # Vektorgröße entspricht der Größe des Embeddings
            distance=Distance.COSINE  # Ähnlichkeitsmetrik
        )
    }
)

# JSON-Datei laden
with open('/Users/alexphan/test tutor2/data3/node_data.json', 'r') as f:
    nodes = json.load(f)

# Batch-Größe definieren (z.B. 1000 Nodes pro Batch)
batch_size = 1000

# Nodes in Batches aufteilen
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

batches = list(chunks(nodes, batch_size))

# Nodes in Batches in Qdrant einfügen
for batch in batches:
    points = [
        PointStruct(
            id=node["node_index"],
            vector=node["embedding"],
            payload={
                "text": node["text"],
                "type": node["type"],
                "module_number": node["module_number"]
            }
        )
        for node in batch
    ]

    client.upsert(
        collection_name='knowledge_graph',
        points=points
    )