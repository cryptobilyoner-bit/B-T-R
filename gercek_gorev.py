import os
import re
from bitir import Hafiza
from ogrenen_planlayici import AkilliKararMotoru, hata_raporu, kaydet

HAFIZA_DOSYASI = "hafiza_gercek.json"
KLASOR = "belgeler"
RAPOR_KLASORU = "calisma"
RAPOR_YOLU = os.path.join(RAPOR_KLASORU, "belgeler_raporu.txt")
MIN_DENEME = 2  # bu kadar denemede hiç başarı yoksa yöntem yasaklanır

ORNEKLER = {
    "ornek1.txt": "Bugün hava çok güzel ve ben BİTİR ile çalışıyorum",
    "ornek2.txt": "Öğrenen sistemler hatalarından ders çıkarır",
    "ornek3.txt": "Küçük adımlar büyük işleri başarır",
}


def ornek_dosyalari_hazirla():
    """'belgeler' klasörü yoksa içine 3 örnek metin dosyası yazar."""
    if not os.path.exists(KLASOR):
        os.makedirs(KLASOR)
        for ad, metin in ORNEKLER.items():
            with open(os.path.join(KLASOR, ad), "w", encoding="utf-8") as f:
                f.write(metin)
        print("Örnek dosyalar 'belgeler' klasörüne yazıldı.")


# ---------- Adım 1: .txt dosyalarını bul ----------
def bul_a(b):
    return [os.path.join(KLASOR, ad) for ad in sorted(os.listdir(KLASOR))
            if ad.endswith(".txt")]


def bul_b(b):  # kasıtlı hata: yanlış uzantıyı arıyor
    return [os.path.join(KLASOR, ad) for ad in sorted(os.listdir(KLASOR))
            if ad.endswith(".md")]


# ---------- Adım 2: dosyaları oku ----------
def oku_a(b):
    sonuc = {}
    for yol in b["yollar"]:
        with open(yol, "r", encoding="utf-8") as f:
            sonuc[yol] = f.read()
    return sonuc


def oku_b(b):  # kasıtlı hata: ascii ile okuyor, Türkçe harfleri okuyamaz
    sonuc = {}
    for yol in b["yollar"]:
        with open(yol, "r", encoding="ascii") as f:
            sonuc[yol] = f.read()
    return sonuc


# ---------- Adım 3: kelime say ----------
def say_a(b):
    return {yol: len(m.split()) for yol, m in b["metinler"].items()}


def say_b(b):  # kasıtlı hata: kelime yerine harf sayıyor
    return {yol: len(m) for yol, m in b["metinler"].items()}


# ---------- Adım 4: rapor yaz ----------
def rapor_a(b):
    os.makedirs(RAPOR_KLASORU, exist_ok=True)
    toplam = sum(b["sayilar"].values())
    satirlar = [os.path.basename(y) + ": " + str(n) + " kelime"
                for y, n in b["sayilar"].items()]
    satirlar.append("TOPLAM: " + str(toplam) + " kelime")
    with open(RAPOR_YOLU, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar))
    return RAPOR_YOLU


def rapor_b(b):  # kasıtlı hata: sayıyı metne çevirmeden yazıyor
    os.makedirs(RAPOR_KLASORU, exist_ok=True)
    with open(RAPOR_YOLU, "w", encoding="utf-8") as f:
        f.write(sum(b["sayilar"].values()))
    return RAPOR_YOLU


# ---------- Her adımın sonucunu kontrol eden fonksiyonlar ----------
def kontrol_bul(sonuc, b):
    return len(sonuc) > 0 and all(os.path.exists(y) for y in sonuc)


def kontrol_oku(sonuc, b):
    return len(sonuc) == len(b["yollar"]) and all(isinstance(m, str) for m in sonuc.values())


def kontrol_say(sonuc, b):
    return all(sonuc.get(y) == len(re.findall(r"\S+", m)) for y, m in b["metinler"].items())


def kontrol_rapor(sonuc, b):
    with open(sonuc, "r", encoding="utf-8") as f:
        icerik = f.read()
    return ("TOPLAM: " + str(sum(b["sayilar"].values()))) in icerik


ADIMLAR = [
    {"ad": "dosyalari_bul", "yontemler": {"bul_a": bul_a, "bul_b": bul_b},
     "kontrol": kontrol_bul, "cikti": "yollar"},
    {"ad": "dosyalari_oku", "yontemler": {"oku_a": oku_a, "oku_b": oku_b},
     "kontrol": kontrol_oku, "cikti": "metinler"},
    {"ad": "kelimeleri_say", "yontemler": {"say_a": say_a, "say_b": say_b},
     "kontrol": kontrol_say, "cikti": "sayilar"},
    {"ad": "rapor_yaz", "yontemler": {"rapor_a": rapor_a, "rapor_b": rapor_b},
     "kontrol": kontrol_rapor, "cikti": "rapor"},
]


def adimi_calistir(motor, hafiza, adim, baglam):
    """Bir adımı çalıştırır. Başarısız olursa hatayı kaydeder ve başka yöntem dener."""
    denenenler = []
    while True:
        kalan = {ad: f for ad, f in adim["yontemler"].items() if ad not in denenenler}
        if not kalan:
            return False

        secilen = motor.yontem_sec(adim["ad"], kalan)
        denenenler.append(secilen)

        try:
            sonuc = kalan[secilen](baglam)
            basarili = adim["kontrol"](sonuc, baglam)
            hata = "" if basarili else "yanlis sonuc: " + str(sonuc)[:80]
        except Exception as e:
            sonuc = None
            basarili = False
            hata = type(e).__name__ + ": " + str(e)[:80]

        if hata:
            hafiza.veri.setdefault("hatalar", []).append(
                {"adim": adim["ad"], "yontem": secilen, "hata": hata}
            )
        hafiza.deneyim_ekle(adim["ad"], secilen, basarili)

        durum = "BAŞARILI" if basarili else "BAŞARISIZ (" + hata + ")"
        print("   Adım '" + adim["ad"] + "': " + secilen + " -> " + durum)

        if basarili:
            baglam[adim["cikti"]] = sonuc
            return True


def ders_cikar(hafiza):
    """Hiç başarılı olmamış yöntemleri yasaklı listesine ekler."""
    dersler = hafiza.veri.setdefault("dersler", {})
    yeni = []
    for adim in ADIMLAR:
        yasaklilar = dersler.setdefault(adim["ad"], [])
        for yontem in adim["yontemler"]:
            toplam, basarili = hafiza.istatistik(adim["ad"], yontem)
            if toplam >= MIN_DENEME and basarili == 0 and yontem not in yasaklilar:
                yasaklilar.append(yontem)
                yeni.append(adim["ad"] + " / " + yontem)
    if yeni:
        kaydet(hafiza)
    return yeni


def main():
    ornek_dosyalari_hazirla()
    hafiza = Hafiza(HAFIZA_DOSYASI)
    motor = AkilliKararMotoru(hafiza)

    for ders in ders_cikar(hafiza):
        print("DERS: " + ders + " hiç başarılı olmadı, artık denenmeyecek.")

    for tur in range(1, 6):
        print("=== GÖREV TURU " + str(tur) + " ===")
        baglam = {}
        tamam = True
        for adim in ADIMLAR:
            if not adimi_calistir(motor, hafiza, adim, baglam):
                tamam = False
                print("   Görev yarım kaldı!")
                break
        if tamam:
            print("   Görev tamamlandı.")
        for ders in ders_cikar(hafiza):
            print("   DERS: " + ders + " hiç başarılı olmadı, artık denenmeyecek.")

    hata_raporu(hafiza)

    print("\n--- YASAKLI YÖNTEMLER ---")
    for gorev, liste in hafiza.veri.get("dersler", {}).items():
        if liste:
            print(gorev + ": " + ", ".join(liste))

    if os.path.exists(RAPOR_YOLU):
        print("\n--- RAPOR (" + RAPOR_YOLU + ") ---")
        with open(RAPOR_YOLU, "r", encoding="utf-8") as f:
            print(f.read())


if __name__ == "__main__":
    main()