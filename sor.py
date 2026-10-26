# sor.py — komut satırından test
from rag import yanitla

while True:
    soru = input("\nSoru (çıkmak için Enter): ").strip()
    if not soru:
        break
    akis, parcalar = yanitla(soru, akis=True)
    for parca in akis:
        print(parca["message"]["content"], end="", flush=True)
    print("\n\nKaynaklar:")
    for i, (_, m, mesafe) in enumerate(parcalar, 1):
        print(f"  [{i}] {m['kaynak']}, s. {m['sayfa']} (mesafe {mesafe:.3f})")
