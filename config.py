# config.py
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = "gemma4:e4b"
EMBED_MODEL = "bge-m3"

BELGE_KLASORU = "belgeler"
DB_KLASORU = "chroma_db"
KOLEKSIYON = "ders_belgeleri"

PARCA_BOYUTU = 1000      # karakter
PARCA_ORTUSME = 200      # karakter
GETIRILECEK_PARCA = 5    # her soruda kaç parça kullanılacak