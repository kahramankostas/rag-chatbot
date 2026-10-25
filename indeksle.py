# indeksle.py
import os, uuid, ollama
from pypdf import PdfReader
from docx import Document
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import config as C

def oku(yol):
    """(sayfa_no, metin) listesi döndürür."""
    uzanti = os.path.splitext(yol)[1].lower()
    if uzanti == ".pdf":
        return [(i + 1, s.extract_text() or "") for i, s in enumerate(PdfReader(yol).pages)]
    if uzanti == ".docx":
        return [(1, "\n".join(p.text for p in Document(yol).paragraphs))]
    if uzanti in (".txt", ".md"):
        with open(yol, encoding="utf-8") as f:
            return [(1, f.read())]
    return []

def parcala(metin, boyut=C.CHUNK_SIZE, tasma=C.CHUNK_OVERLAP):
    """Paragraf sınırlarını koruyarak parçalara böler."""
    paragraflar = [p.strip() for p in metin.split("\n") if p.strip()]
    parcalar, mevcut = [], ""
    for p in paragraflar:
        if len(mevcut) + len(p) > boyut and mevcut:
            parcalar.append(mevcut)
            mevcut = mevcut[-tasma:]  # taşma: bağlam kopmasın
        mevcut += (" " if mevcut else "") + p
    if mevcut:
        parcalar.append(mevcut)
    return parcalar

def embed(metinler):
    return ollama.embed(model=C.EMBED_MODEL, input=metinler)["embeddings"]

def main():
    qd = QdrantClient(url=C.QDRANT_URL)
    boyut = len(embed(["test"])[0])
    if qd.collection_exists(C.COLLECTION):
        qd.delete_collection(C.COLLECTION)          # temiz yeniden indeksleme
    qd.create_collection(C.COLLECTION,
        vectors_config=VectorParams(size=boyut, distance=Distance.COSINE))

    toplam = 0
    for dosya in sorted(os.listdir(C.BELGE_KLASORU)):
        yol = os.path.join(C.BELGE_KLASORU, dosya)
        for sayfa, metin in oku(yol):
            parcalar = parcala(metin)
            if not parcalar:
                continue
            vektorler = embed(parcalar)
            noktalar = [PointStruct(id=str(uuid.uuid4()), vector=v,
                          payload={"metin": p, "kaynak": dosya, "sayfa": sayfa})
                        for p, v in zip(parcalar, vektorler)]
            qd.upsert(C.COLLECTION, points=noktalar)
            toplam += len(noktalar)
        print(f"✓ {dosya}")
    print(f"Toplam {toplam} parça indekslendi.")

if __name__ == "__main__":
    main()