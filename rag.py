# rag.py
import chromadb
from ollama import Client

import config

_llm = Client(host=config.OLLAMA_HOST)
_kol = chromadb.PersistentClient(path=config.DB_KLASORU).get_collection(config.KOLEKSIYON)

SISTEM_ISTEMI = """Sen 1416 sayılı Kanun kapsamındaki YLSY bursu hakkında öğrencilere yardım eden bir asistansın.
Kurallar:
1. Yalnızca BAĞLAM'daki numaralı kaynaklara dayanarak yanıt ver; kendi genel bilgini ekleme.
2. Yanıt bağlamda açıkça yoksa yalnızca şu cümleyi yaz: "Bu sorunun yanıtı belgelerde bulunmuyor."
3. Soru başka bir burs veya program (KYK, Erasmus, Fulbright vb.) ya da belgelerde olmayan bir yıl hakkındaysa, 1416 bilgisini onun yerine verme; 2. kuraldaki cümleyi yaz.
4. Kullandığın her bilginin sonuna kaynak numarasını [1], [2] biçiminde ekle. Sayfa, madde veya dosya adı yazma.
5. Türkçe, kısa ve öğrenci düzeyinde yaz."""


def ara(soru: str, k: int = config.GETIRILECEK_PARCA):
    vektor = _llm.embed(model=config.EMBED_MODEL, input=[soru])["embeddings"][0]
    sonuc = _kol.query(query_embeddings=[vektor], n_results=k)
    return list(zip(sonuc["documents"][0], sonuc["metadatas"][0], sonuc["distances"][0]))


def baglam_olustur(parcalar) -> str:
    return "\n\n".join(f"[{i}]\n{metin}" for i, (metin, _, _) in enumerate(parcalar, 1))


def yanitla(soru: str, akis: bool = False):
    parcalar = ara(soru)
    mesajlar = [
        {"role": "system", "content": SISTEM_ISTEMI},
        {"role": "user", "content": f"BAĞLAM:\n{baglam_olustur(parcalar)}\n\nSORU: {soru}"},
    ]
    yanit = _llm.chat(
        model=config.LLM_MODEL,
        messages=mesajlar,
        stream=akis,
        think=False,
        options={"temperature": 0.2, "num_ctx": 8192},
    )
    return yanit, parcalar
