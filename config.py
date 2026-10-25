# config.py
CHAT_MODEL = "gemma4:e2b"      # veya gemma4:12b
EMBED_MODEL = "bge-m3"
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "belgeler"
BELGE_KLASORU = "/opt/rag-chatbot/belgeler"

CHUNK_SIZE = 1000        # karakter
CHUNK_OVERLAP = 200      # karakter
TOP_K = 5                # modele verilecek parça sayısı
SCORE_THRESHOLD = 0.55   # bunun altı = "alakasız" (Adım 7'de ayarlanır)

RET_MESAJI = ("Bu sorunun cevabı elimdeki belgelerde yer almıyor. "
              "Lütfen sorunuzu farklı ifade edin veya ilgili birime başvurun.")