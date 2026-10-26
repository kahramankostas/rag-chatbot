# degerlendir.py
# test_sorular.json içindeki soruları RAG sistemine sorar, sonuçları puanlar
# ve sonuclar.csv dosyasına yazar. Kullanım: python degerlendir.py
import csv
import json
import time
from pathlib import Path

from rag import yanitla

RED_IFADESI = "belgelerde bulunmuyor"


def kucult(metin: str) -> str:
    # Python'un lower() fonksiyonu I/İ harflerini Türkçeye uygun çevirmez
    return metin.replace("I", "ı").replace("İ", "i").lower()


def kelimeler_var(yanit: str, gruplar: list[str]) -> bool:
    # Her grup için en az bir alternatif yanıtta geçmeli ("2.50|2,50" gibi)
    y = kucult(yanit)
    return all(any(kucult(a) in y for a in g.split("|")) for g in gruplar)


def main():
    sorular = json.load(open("test_sorular.json", encoding="utf-8"))
    satirlar, sureler = [], []
    puan = {"kaynak": 0, "sayfa": 0, "yanit": 0, "red": 0}
    var_sayisi = sum(s["belgede_var"] for s in sorular)
    yok_sayisi = len(sorular) - var_sayisi

    for s in sorular:
        t0 = time.perf_counter()
        cevap, parcalar = yanitla(s["soru"])
        sure = time.perf_counter() - t0
        sureler.append(sure)

        metin = cevap["message"]["content"].strip()
        getirilen = [(Path(m["kaynak"]).name, m["sayfa"]) for _, m, _ in parcalar]
        reddetti = RED_IFADESI in kucult(metin)

        if s["belgede_var"]:
            kaynak_ok = any(ad in s["kaynak"] for ad, _ in getirilen)
            sayfa_ok = (s["kaynak"][0], s["sayfa"]) in getirilen
            yanit_ok = kelimeler_var(metin, s["anahtar_kelimeler"]) and not reddetti
            puan["kaynak"] += kaynak_ok
            puan["sayfa"] += sayfa_ok
            puan["yanit"] += yanit_ok
            durum = "DOĞRU" if yanit_ok else ("KAYNAK YOK" if not kaynak_ok else "YANIT HATALI")
        else:
            kaynak_ok = sayfa_ok = yanit_ok = None
            puan["red"] += reddetti
            durum = "DOĞRU RED" if reddetti else "UYDURDU"

        print(f"{s['id']}  {durum:<12} {sure:5.1f} sn  {s['soru']}")
        satirlar.append({
            "id": s["id"],
            "durum": durum,
            "soru": s["soru"],
            "beklenen_yanit": s["beklenen_yanit"],
            "model_yaniti": metin,
            "beklenen_kaynak": f"{s['kaynak'][0]} s.{s['sayfa']}" if s["kaynak"] else "-",
            "getirilen_parcalar": " | ".join(f"{ad} s.{sf}" for ad, sf in getirilen),
            "kaynak_isabet": kaynak_ok,
            "sayfa_isabet": sayfa_ok,
            "sure_sn": round(sure, 1),
        })

    # Excel'in Türkçe ayarlarında doğru açılması için ; ayırıcı ve BOM
    with open("sonuclar.csv", "w", newline="", encoding="utf-8-sig") as f:
        yazici = csv.DictWriter(f, fieldnames=satirlar[0].keys(), delimiter=";")
        yazici.writeheader()
        yazici.writerows(satirlar)

    oran = lambda x, n: f"{x}/{n} (%{100 * x / n:.0f})"
    print("\n========== ÖZET ==========")
    print(f"Doğru belge getirildi : {oran(puan['kaynak'], var_sayisi)}   hedef ≥ %85")
    print(f"Doğru sayfa getirildi : {oran(puan['sayfa'], var_sayisi)}")
    print(f"Doğru yanıt (otomatik): {oran(puan['yanit'], var_sayisi)}   hedef ≥ %80")
    print(f"Uydurmama (red)       : {oran(puan['red'], yok_sayisi)}   hedef %100")
    print(f"Ortalama yanıt süresi : {sum(sureler) / len(sureler):.1f} sn")
    print("Ayrıntılar: sonuclar.csv")


if __name__ == "__main__":
    main()
