# ingest.py
import re
import unicodedata
from pathlib import Path

import chromadb
import pymupdf
from ollama import Client

import config

llm = Client(host=config.OLLAMA_HOST)


def temizle(metin: str) -> str:
    metin = unicodedata.normalize("NFC", metin)          # Türkçe karakterleri tek biçime getir
    metin = re.sub(r"(\w)-\n(\w)", r"\1\2", metin)       # satır sonu tirelemesini birleştir
    metin = re.sub(r"[ \t]+", " ", metin)
    metin = re.sub(r"\n{3,}", "\n\n", metin)
    return metin.strip()


def parcala(metin: str, boyut: int, ortusme: int) -> list[str]:
    parcalar, bas = [], 0
    while bas < len(metin):
        son = min(bas + boyut, len(metin))
        if son < len(metin):
            # Mümkünse cümle veya satır sonunda kes
            kesim = max(metin.rfind(". ", bas, son), metin.rfind("\n", bas, son))
            if kesim > bas + boyut // 2:
                son = kesim + 1
        parca = metin[bas:son].strip()
        if len(parca) > 50:
            parcalar.append(parca)
        if son >= len(metin):
            break
        # Örtüşme bölgesinde bir cümle/satır başı ara; yoksa en azından kelime başından başla
        yeni = son - ortusme
        cumle = max(metin.rfind(". ", yeni, son), metin.rfind("\n", yeni, son))
        if cumle > bas:
            yeni = cumle + 1
        else:
            bosluk = metin.find(" ", yeni, son)
            yeni = bosluk + 1 if bosluk != -1 else son
        bas = max(yeni, bas + 1)
    return parcalar


def main():
    db = chromadb.PersistentClient(path=config.DB_KLASORU)
    try:
        db.delete_collection(config.KOLEKSIYON)
    except Exception:
        pass
    kol = db.create_collection(config.KOLEKSIYON)

    kok = Path(config.BELGE_KLASORU)
    pdfler = sorted(kok.glob("**/*.pdf"))
    print(f"{len(pdfler)} PDF bulundu.")

    for pdf in pdfler:
        ad = str(pdf.relative_to(kok))
        ids, metinler, metalar = [], [], []
        with pymupdf.open(pdf) as belge:
            for sayfa_no, sayfa in enumerate(belge, start=1):
                metin = temizle(sayfa.get_text())
                for i, parca in enumerate(parcala(metin, config.PARCA_BOYUTU, config.PARCA_ORTUSME)):
                    ids.append(f"{ad}|s{sayfa_no}|p{i}")
                    metinler.append(parca)
                    metalar.append({"kaynak": ad, "sayfa": sayfa_no})

        if not metinler:
            print(f"UYARI: {ad} içinde metin yok (taranmış PDF olabilir, OCR gerekir).")
            continue

        for i in range(0, len(metinler), 32):          # 32'lik partilerle vektörle
            parti = metinler[i:i + 32]
            vektorler = llm.embed(model=config.EMBED_MODEL, input=parti)["embeddings"]
            kol.add(ids=ids[i:i + 32], documents=parti,
                    embeddings=vektorler, metadatas=metalar[i:i + 32])
        print(f"{ad}: {len(metinler)} parça eklendi.")

    print(f"Bitti. Toplam {kol.count()} parça.")


if __name__ == "__main__":
    main()
