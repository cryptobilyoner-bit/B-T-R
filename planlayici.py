import os
from bitir import Hafiza, KararMotoru

HAFIZA_DOSYASI = "hafiza_gorev.json"
KLASOR = "calisma"
METIN = "bitir ogrenen bir sistemdir bitir hata yapar ve hatalarindan ogrenir"


# ---------- Adım 1: dosya oluştur ----------
def olustur_a(b):
    os.makedirs(KLASOR, exist_ok=True)
    yol = os.path.join(KLASOR, "metin.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(METIN)
    return yol


def olustur_b(b):  # kasıtlı hata: olmayan klasöre yazmaya çalışıyor
    yol = os.path.join("olmayan_klasor", "metin.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(METIN)
    return yol


# ---------- Adım 2: dosyayı oku ----------
def oku_a(b):
    with open(b["yol"], "r", encoding="utf-8") as f:
        return f.read()


def oku_b(b):  # kasıtlı hata: yanlış dosya adı
    with open(b["yol"] + "x", "r", encoding="utf-8") as f:
        return f.read()


# ---------- Adım 3: kelime say ----------
def say_a(b):
    return len(b["metin"].split())


def say_b(b):  # kasıtlı hata: boşlukları sayıyor, kelimeleri değil
    return b["metin"].count(" ")


# ---------- Adım 4: rapor yaz ----------
def rapor_a(b):
    yol = os.path.join(KLASOR, "rapor.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("Kelime sayisi: " + str(b["kelime"]))
    return yol


def rapor_b(b):  # kasıtlı hata: sayıyı metne çevirmeden yazıyor
    yol = os.path.join(KLASOR, "rapor.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(b["kelime"])
    return yol


# ---------- Her adımın sonucunu kontrol eden fonksiyonlar ----------
def kontrol_olustur(sonuc):
    return os.path.exists(sonuc)


def kontrol_oku(sonuc):
    return sonuc == METIN


def kontrol_say(sonuc):
    return sonuc == 10


def kontrol_rapor(sonuc):
    with open(sonuc, "r", encoding="utf-8") as f:
        return "10" in f.read()


# ---------- Görevin adımları ----------
ADIMLAR = [
    {"ad": "dosya_olustur", "yontemler": {"olustur_a": olustur_a, "olustur_b": olustur_b},
     "kontrol": kontrol_olustur, "cikti": "yol"},
    {"ad": "dosyayi_oku", "yontemler": {"oku_a": oku_a, "oku_b": oku_b},
     "kontrol": kontrol_oku, "cikti": "metin"},
    {"ad": "kelime_say", "yontemler": {"say_a": say_a, "say_b": say_b},
     "kontrol": kontrol_say, "cikti": "kelime"},
    {"ad": "rapor_yaz", "yontemler": {"rapor_a": rapor_a, "rapor_b": rapor_b},
     "kontrol": kontrol_rapor, "cikti": "rapor"},
]


def adimi_calistir(motor, hafiza, adim, baglam):
    """Bir adımı çalıştırır. Yöntem başarısız olursa hatayı kaydeder ve başka yöntem dener."""
    denenenler = []
    while True:
        kalan = {ad: f for ad, f in adim["yontemler"].items() if ad not in denenenler}
        if not kalan:
            return False  # tüm yöntemler denendi, adım başarısız

        secilen = motor.yontem_sec(adim["ad"], kalan)
        denenenler.append(secilen)

        try:
            sonuc = kalan[secilen](baglam)
            basarili = adim["kontrol"](sonuc)
            hata = "" if basarili else "yanlis sonuc: " + str(sonuc)
        except Exception as e:
            sonuc = None
            basarili = False
            hata = type(e).__name__ + ": " + str(e)

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


def main():
    hafiza = Hafiza(HAFIZA_DOSYASI)
    motor = KararMotoru(hafiza)

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

    print("\n--- Hafızadaki toplam durum ---")
    for adim in ADIMLAR:
        for y in adim["yontemler"]:
            toplam, basarili = hafiza.istatistik(adim["ad"], y)
            print(adim["ad"] + " / " + y + ": " + str(toplam) + " deneme, " + str(basarili) + " başarılı")
    print("Kayıtlı toplam hata: " + str(len(hafiza.veri.get("hatalar", []))))


if __name__ == "__main__":
    main()