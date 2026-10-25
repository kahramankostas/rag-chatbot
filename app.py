# app.py
import ollama
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
import config as C

app = FastAPI()
qd = QdrantClient(url=C.QDRANT_URL)

SISTEM_ISTEMI = """Sen bir belge asistanısın. KURALLAR:
1. YALNIZCA <belgeler> etiketi içindeki metinleri kullanarak cevap ver.
2. Kendi genel bilgini, tahminini veya varsayımını ASLA kullanma.
3. Cevap belgelerde açıkça yoksa veya emin değilsen, başka hiçbir şey
   yazmadan yalnızca şunu yaz: CEVAP_YOK
4. Her bilginin sonunda köşeli parantezle kaynak numarasını ver, örn. [1].
5. Belgelerde olmayan sayı, tarih, isim UYDURMA.
6. Kısa, net ve Türkçe cevap ver."""

class Soru(BaseModel):
    soru: str

def ara(soru):
    vektor = ollama.embed(model=C.EMBED_MODEL, input=[soru])["embeddings"][0]
    return qd.query_points(C.COLLECTION, query=vektor, limit=C.TOP_K,
                           score_threshold=C.SCORE_THRESHOLD,
                           with_payload=True).points

@app.post("/sor")
def sor(s: Soru):
    sonuclar = ara(s.soru)

    # KAPI 1: alakalı parça yoksa modeli hiç çağırma
    if not sonuclar:
        return {"cevap": C.RET_MESAJI, "kaynaklar": []}

    baglam = "\n\n".join(
        f"[{i+1}] (Kaynak: {r.payload['kaynak']}, s. {r.payload['sayfa']})\n{r.payload['metin']}"
        for i, r in enumerate(sonuclar))

    yanit = ollama.chat(
        model=C.CHAT_MODEL,
        messages=[
            {"role": "system", "content": SISTEM_ISTEMI},
            {"role": "user", "content": f"<belgeler>\n{baglam}\n</belgeler>\n\nSoru: {s.soru}"},
        ],
        options={"temperature": 0, "num_ctx": 8192},
    )
    cevap = yanit["message"]["content"].strip()

    # KAPI 2: model cevap yok dediyse
    if "CEVAP_YOK" in cevap:
        return {"cevap": C.RET_MESAJI, "kaynaklar": []}

    kaynaklar = [{"no": i+1, "dosya": r.payload["kaynak"], "sayfa": r.payload["sayfa"],
                  "skor": round(r.score, 3)} for i, r in enumerate(sonuclar)]
    return {"cevap": cevap, "kaynaklar": kaynaklar}

@app.get("/", response_class=HTMLResponse)
def arayuz():
    with open("index.html", encoding="utf-8") as f:
        return f.read()