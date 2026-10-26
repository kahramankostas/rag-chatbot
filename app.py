# app.py — YLSY Asistanı
import re
from pathlib import Path

import streamlit as st

from rag import yanitla

# Belge dosya adlarının öğrenciye gösterilecek okunur adları
BELGE_ADLARI = {
    "2025_yili_1416_burslari_basvuru_ve_tercih_kilavuzu.pdf":
        "2025 Yılı 1416 Bursları Başvuru ve Tercih Kılavuzu",
    "turk_ogrencilerin_yabanci_ulkelerde_ogrenimleri_hakkinda_yonetmelik.pdf":
        "Türk Öğrencilerin Yabancı Ülkelerde Öğrenimleri Hakkında Yönetmelik",
    "1416_yurt_disinda_ogrenim_gorecek_ogrencilere_yapilacak_odemeler_hakkinda_teblig.pdf":
        "Öğrencilere Yapılacak Ödemeler Hakkında Tebliğ",
    "ek1_burs_tutarlari.pdf":
        "Tebliğ Ek-1: Ülkelere Göre Burs Tutarları",
    "1416_sayili_kanun_kapsaminda_yabanci_dil_ogrenimine_iliskin_usul_ve_esaslar.pdf":
        "Yabancı Dil Öğrenimine İlişkin Usul ve Esaslar",
    "1416_kapsaminda_doktora_sonrasi_arastirma_iznine_iliskin_usul_ve_esaslar.pdf":
        "Doktora Sonrası Araştırma İznine İlişkin Usul ve Esaslar",
    "1416_sayili_ecnebi_memleketlere_gonderilecek_talebe_hakkinda_kanun.pdf":
        "1416 Sayılı Kanun",
}

ORNEK_SORULAR = [
    "Almanya'da lisansüstü aylık bursum ne kadar?",
    "Mecburi hizmet sürem nasıl hesaplanır?",
    "Konferansa katılırsam masraflarım karşılanır mı?",
    "Doktora sonrası araştırma iznine nasıl başvururum?",
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap');

:root {
  --bordo: #6E1F2E;
  --bordo-koyu: #561724;
  --yaldiz: #C9A54E;
  --murekkep: #1D2433;
  --gri: #5B6270;
  --cizgi: #DDE1E7;
}
.stApp .stMarkdown p, .stApp .stMarkdown li, .stApp textarea, .stApp button p {
  font-family: 'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif;
}
.stApp .stMarkdown p, .stApp .stMarkdown li { font-size: 1rem; line-height: 1.6; }
.block-container { max-width: 46rem; padding-top: 2rem; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

/* Başlık: pasaport kapağı */
.kapak {
  background: var(--bordo);
  border-radius: 6px;
  padding: 1.75rem 1.75rem 1.5rem;
  margin-bottom: 1.25rem;
  color: #F6F1E7;
}
.kapak h1 {
  font-family: 'Source Serif 4', Georgia, serif;
  font-weight: 600;
  font-size: 2.1rem;
  line-height: 1.15;
  margin: 0 0 0.75rem;
  padding: 0;
  color: #F6F1E7;
}
.kapak .yaldiz { width: 3rem; height: 2px; background: var(--yaldiz); margin-bottom: 0.9rem; }
.kapak p { margin: 0; font-size: 1rem; line-height: 1.55; color: #EDE3D3; max-width: 36rem; }

.aciklama { color: var(--gri); font-size: 0.95rem; line-height: 1.55; margin: 0 0 1.5rem; }

/* Dipnotlar */
sup.dn { color: var(--bordo); font-weight: 600; font-size: 0.72em; margin-left: 1px; }
.dipnotlar {
  border-top: 1px solid var(--cizgi);
  margin-top: 0.9rem;
  padding-top: 0.6rem;
}
.dipnotlar .satir {
  display: flex; gap: 0.6rem;
  font-size: 0.85rem; line-height: 1.45; color: var(--gri);
  margin: 0.2rem 0;
}
.dipnotlar .no { color: var(--bordo); font-weight: 600; min-width: 1rem; text-align: right; }
.dipnotlar .sayfa { white-space: nowrap; }

/* Örnek sorular */
.ornek-baslik { color: var(--gri); font-size: 0.9rem; margin: 0.25rem 0 0.5rem; }
.stButton button {
  width: 100%; text-align: left; justify-content: flex-start;
  border: 1px solid var(--cizgi); background: #FFFFFF; color: var(--murekkep);
  min-height: 3.2rem;
}
.stButton button:hover { border-color: var(--bordo); color: var(--bordo); }
.stButton button:focus-visible { outline: 2px solid var(--bordo); outline-offset: 2px; }

section[data-testid="stSidebar"] h3 {
  font-family: 'Source Serif 4', Georgia, serif; font-weight: 600; color: var(--murekkep);
}
</style>
"""

# [1], [1, 2] ve modelin ara sıra yazdığı [1, 6.3], [8-1] gibi biçimler
ATIF = re.compile(r"\s?\[(\d[\d\s,.\-–]*)\]")
TAM_SAYI = re.compile(r"(?<![\d.\-–])\d+(?![\d.\-–])")  # 6.3, 8-1 gibi madde numaralarını atla
ARDISIK = re.compile(r"(\[\d[\d\s,.\-–]*)\]\s*,?\s*\[(?=\d)")  # "[1], [2]" -> "[1, 2"
ESKI_ATIF = re.compile(r"\s?\[[^\]]*\.pdf[^\]]*\]")  # eski "[dosya.pdf, s. 7]" biçimi


def belge_adi(yol: str) -> str:
    ad = Path(yol).name
    return BELGE_ADLARI.get(ad, Path(ad).stem.replace("_", " ").capitalize())


def dipnotlara_cevir(metin: str, parcalar):
    """[1], [2] atıflarını sırayla 1, 2, 3 diye numaralanan dipnotlara çevirir.
    Aynı belge ve sayfayı gösteren parçalar tek dipnotta birleşir."""
    metin = ESKI_ATIF.sub("", metin)
    while ARDISIK.search(metin):
        metin = ARDISIK.sub(r"\1, ", metin)
    yeni_no = {}   # (belge, sayfa) -> dipnot no
    eslesme = {}   # parça no -> dipnot no

    for grup in ATIF.findall(metin):
        for parca_no in (int(x) for x in TAM_SAYI.findall(grup)):
            if parca_no in eslesme or not 1 <= parca_no <= len(parcalar):
                continue
            m = parcalar[parca_no - 1][1]
            anahtar = (belge_adi(m["kaynak"]), m["sayfa"])
            yeni_no.setdefault(anahtar, len(yeni_no) + 1)
            eslesme[parca_no] = yeni_no[anahtar]

    def degistir(e):
        nolar = sorted({eslesme[int(x)] for x in TAM_SAYI.findall(e.group(1)) if int(x) in eslesme})
        return f"<sup class='dn'>{','.join(map(str, nolar))}</sup>" if nolar else ""

    metin = ATIF.sub(degistir, metin)
    metin = re.sub(r"(</sup>)\s*\(\d+\)", r"\1", metin)  # atıftan sonra kalan "(5)" gibi artıklar
    metin = re.sub(r"(<sup class='dn'>[\d,]+</sup>)(?:,?\s*\1)+", r"\1", metin)
    kaynaklar = [(no, ad, sayfa) for (ad, sayfa), no in yeni_no.items()]
    return metin.strip(), kaynaklar


def dipnot_html(kaynaklar) -> str:
    if not kaynaklar:
        return ""
    satirlar = "".join(
        f"<div class='satir'><span class='no'>{no}</span>"
        f"<span>{ad}, <span class='sayfa'>s. {sayfa}</span></span></div>"
        for no, ad, sayfa in kaynaklar
    )
    return f"<div class='dipnotlar'>{satirlar}</div>"


def mesaj_goster(m):
    with st.chat_message(m["rol"]):
        if m["rol"] == "user":
            st.markdown(m["metin"])  # öğrencinin yazdığı metne HTML izni verme
        else:
            st.markdown(m["metin"] + m.get("dipnot", ""), unsafe_allow_html=True)


def ornek_sec(soru: str):
    st.session_state.bekleyen = soru


# ---------------- Sayfa ----------------
st.set_page_config(page_title="YLSY Asistanı", page_icon="🎓", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

if "gecmis" not in st.session_state:
    st.session_state.gecmis = []

with st.sidebar:
    st.markdown("### Bu asistan hakkında")
    st.markdown(
        "Yanıtlar yalnızca aşağıdaki resmî belgelere dayanır. "
        "Bilgilendirme amaçlıdır; işleminizi yapmadan önce yurt dışı "
        "temsilciliğinize veya YYEGM'ye danışın."
    )
    st.markdown("### Kullanılan belgeler")
    st.markdown("\n".join(f"- {ad}" for ad in BELGE_ADLARI.values()))
    st.markdown("### Resmî iletişim")
    st.markdown(
        "- [yyegm.meb.gov.tr](https://yyegm.meb.gov.tr)\n"
        "- [rebus.meb.gov.tr](https://rebus.meb.gov.tr)\n"
        "- MEB İletişim Merkezi: 444 0 632"
    )
    if st.session_state.gecmis and st.button("Yeni sohbet başlat"):
        st.session_state.gecmis = []
        st.rerun()

st.markdown(
    """
<div class="kapak">
  <h1>YLSY Asistanı</h1>
  <div class="yaldiz"></div>
  <p>1416 sayılı Kanun kapsamında yurt dışında lisansüstü öğrenim gören
  resmî burslu öğrenciler için soru-cevap asistanı.</p>
</div>
""",
    unsafe_allow_html=True,
)

yazilan = st.chat_input("Sorunuzu yazın, örneğin: Tez masraflarım karşılanıyor mu?")
soru = yazilan or st.session_state.pop("bekleyen", None)

if not st.session_state.gecmis and not soru:
    st.markdown(
        "<p class='aciklama'>Burs tutarları, mecburi hizmet, dil öğrenimi, izinler, "
        "sağlık giderleri ve doktora sonrası araştırma gibi konularda sorabilirsiniz. "
        "Her yanıtın altında bilginin alındığı belge ve sayfa yer alır.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<p class='ornek-baslik'>Şunlardan biriyle başlayabilirsiniz:</p>",
                unsafe_allow_html=True)
    sol, sag = st.columns(2)
    for i, ornek in enumerate(ORNEK_SORULAR):
        (sol if i % 2 == 0 else sag).button(
            ornek, key=f"ornek{i}", on_click=ornek_sec, args=(ornek,)
        )

for m in st.session_state.gecmis:
    mesaj_goster(m)

if soru:
    kullanici = {"rol": "user", "metin": soru}
    st.session_state.gecmis.append(kullanici)
    mesaj_goster(kullanici)

    with st.chat_message("assistant"):
        alan = st.empty()
        try:
            alan.markdown("_Belgeler taranıyor…_")
            akis, parcalar = yanitla(soru, akis=True)
            ham = ""
            for parca in akis:
                ham += parca["message"]["content"]
                alan.markdown(ATIF.sub("", ESKI_ATIF.sub("", ham)) + " ▍")
            metin, kaynaklar = dipnotlara_cevir(ham, parcalar)
            dipnot = dipnot_html(kaynaklar)
        except Exception:
            metin = ("Yanıt şu anda oluşturulamadı: dil modeline ulaşılamıyor. "
                     "Birkaç dakika sonra tekrar deneyin.")
            dipnot = ""
        alan.markdown(metin + dipnot, unsafe_allow_html=True)

    st.session_state.gecmis.append({"rol": "assistant", "metin": metin, "dipnot": dipnot})
