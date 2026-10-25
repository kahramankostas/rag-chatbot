# skor_test.py
import ollama
from qdrant_client import QdrantClient
import config as C

qd = QdrantClient(url=C.QDRANT_URL)
sorular = [
    "Belgede cevabı olan soru 1",
    "Belgede cevabı OLMAYAN soru 1",
    # ...
]
for s in sorular:
    v = ollama.embed(model=C.EMBED_MODEL, input=[s])["embeddings"][0]
    r = qd.query_points(C.COLLECTION, query=v, limit=3, with_payload=True).points
    print(f"{r[0].score:.3f}  {s}  →  {r[0].payload['kaynak']}")