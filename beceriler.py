import csv
import os
import shutil

from bitir import Hafiza
from ogrenen_planlayici import AkilliKararMotoru, hata_raporu, kaydet
from gercek_gorev import adimi_calistir

HAFIZA_DOSYASI = "hafiza_beceriler.json"
KAYNAK = "duzenlenecek"
CALISMA = "calisma"
RAPOR_YOLU = os.path.join(CALISMA, "duzen_raporu.txt")
MIN_DENEME = 2  # bu kadar denemede hiç başarı yoksa yöntem yasaklanır

ORNEKLER = {
    "not1.txt": "Bugun BITIR yeni beceriler ogreniyor\n",
    "not2.txt": "Kucuk adimlar buyuk isleri basarir\n",
    "urunler.csv": "ad,adet,fiyat\nelma,3,10\narmut,2,15.5\nkiraz,5,8\n",
    "ozet.md": "# Ozet\nBu bir deneme dosyasidir.\n",
}


def ornek_dosyalari_hazirla():
    """'duzenlenecek' klasörü yoksa içine örnek dosyalar yazar."""
    if not os.path.exists(KAYNAK):
        os.makedirs(KAYNAK)
        for ad, metin in ORNEKLER.items():
            with open(os.path.join(KAYNAK, ad), "w", encoding="utf-8") as f:
                f.write(metin)
        print("Örnek dosyalar 'duzenlenecek' klasörüne yazıldı.")


def uzanti(ad):
    uz = os.path.splitext(ad)[1].lower().lstrip(".")
    return uz if uz else "uzantisiz"


def tum_dosyalar():
    return [os.path.join(KAYNAK, a) for a in sorted(os.listdir(KAYNAK))
            if os.path.isfile(os.path.join(KAYNAK, a))]


# ---------- Beceri 1: dosyaları listele ----------
def listele_a(b):
    return tum_dosyalar()


def listele_b(b):  # kasıtlı hata: sadece .txt dosyalarını listeliyor
    return [y for y in tum_dosyalar() if y.lower().endswith(".txt")]


# ---------- Beceri 2: yedek al ----------
def yedek_a(b):
    hedef = os.path.join(CALISMA, "yedek")
    os.makedirs(hedef, exist_ok=True)
    for yol in b["dosyalar"]:
        shutil.copy2(yol, hedef)
    return hedef


def yedek_b(b):  # kasıtlı hata: olmayan klasöre kopyalıyor
    hedef = os.path.join(CALISMA, "olmayan_yedek", "klasor")
    for yol in b["dosyalar"]:
        shutil.copy2(yol, hedef)
    return hedef


# ---------- Beceri 3: türüne göre ayır ----------
def ayir_a(b):
    gruplar = {}
    for yol in b["dosyalar"]:
        ad = os.path.basename(yol)
        uz = uzanti(ad)
        hedef = os.path.join(CALISMA, "duzenli", uz)
        os.makedirs(hedef, exist_ok=True)
        shutil.copy2(yol, os.path.join(hedef, ad))
        gruplar.setdefault(uz, []).append(ad)
    return gruplar


def ayir_b(b):  # kasıtlı hata: uzantıya değil, dosya adının ilk harfine göre ayırıyor
    gruplar = {}
    for yol in b["dosyalar"]:
        ad = os.path.basename(yol)
        harf = ad[0].lower()
        hedef = os.path.join(CALISMA, "duzenli_hatali", harf)
        os.makedirs(hedef, exist_ok=True)
        shutil.copy2(yol, os.path.join(hedef, ad))
        gruplar.setdefault(harf, []).append(ad)
    return gruplar


# ---------- Beceri 4: CSV oku ----------
def csv_oku(b, ayirici):
    satir_sayisi = 0
    adet_toplam = 0
    dosya_sayisi = 0
    for yol in b["dosyalar"]:
        if yol.lower().endswith(".csv"):
            dosya_sayisi += 1
            with open(yol, "r", encoding="utf-8", newline="") as f:
                for satir in csv.DictReader(f, delimiter=ayirici):
                    satir_sayisi += 1
                    try:
                        adet_toplam += int(satir.get("adet", 0))
                    except (ValueError, TypeError):
                        pass
    return {"dosya": dosya_sayisi, "satir": satir_sayisi, "adet_toplam": adet_toplam}


def csv_a(b):
    return csv_oku(b, ",")


def csv_b(b):  # kasıtlı hata: ayırıcı olarak noktalı virgül kullanıyor
    return csv_oku(b, ";")


# ---------- Beceri 5: rapor yaz ----------
def rapor_a(b):
    os.makedirs(CALISMA, exist_ok=True)
    satirlar = ["TOPLAM DOSYA: " + str(len(b["dosyalar"]))]
    for uz, adlar in sorted(b["gruplar"].items()):
        satirlar.append("." + uz + ": " + str(len(adlar)) + " dosya (" + ", ".join(adlar) + ")")
    c = b["csv"]
    satirlar.append("CSV: " + str(c["dosya"]) + " dosya, " + str(c["satir"])
                    + " satir, adet toplami " + str(c["adet_toplam"]))
    with open(RAPOR_YOLU, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar))
    return RAPOR_YOLU


def rapor_b(b):  # kasıtlı hata: sayıyı metne çevirmeden yazıyor
    os.makedirs(CALISMA, exist_ok=True)
    with open(RAPOR_YOLU, "w", encoding="utf-8") as f:
        f.write(len(b["dosyalar"]))
    return RAPOR_YOLU


# ---------- Her becerinin sonucunu bağımsız kontrol eden fonksiyonlar ----------
def kontrol_listele(sonuc, b):
    beklenen = sorted(os.path.join(KAYNAK, a) for a in os.listdir(KAYNAK)
                      if os.path.isfile(os.path.join(KAYNAK, a)))
    return sorted(sonuc) == beklenen


def kontrol_yedek(sonuc, b):
    return all(os.path.exists(os.path.join(sonuc, os.path.basename(y))) for y in b["dosyalar"])


def kontrol_ayir(sonuc, b):
    beklenen = {}
    for yol in b["dosyalar"]:
        ad = os.path.basename(yol)
        beklenen.setdefault(uzanti(ad), []).append(ad)
    if {k: sorted(v) for k, v in sonuc.items()} != {k: sorted(v) for k, v in beklenen.items()}:
        return False
    return all(os.path.exists(os.path.join(CALISMA, "duzenli", uz, ad))
               for uz, adlar in sonuc.items() for ad in adlar)


def kontrol_csv(sonuc, b):
    satir_sayisi = 0
    adet_toplam = 0
    dosya_sayisi = 0
    for yol in b["dosyalar"]:
        if yol.lower().endswith(".csv"):
            dosya_sayisi += 1
            with open(yol, "r", encoding="utf-8") as f:
                satirlar = [s.strip() for s in f.read().splitlines() if s.strip()]
            if not satirlar:
                continue
            basliklar = satirlar[0].split(",")
            satir_sayisi += len(satirlar) - 1
            if "adet" in basliklar:
                i = basliklar.index("adet")
                for s in satirlar[1:]:
                    try:
                        adet_toplam += int(s.split(",")[i])
                    except (ValueError, IndexError):
                        pass
    return sonuc == {"dosya": dosya_sayisi, "satir": satir_sayisi, "adet_toplam": adet_toplam}


def kontrol_rapor(sonuc, b):
    with open(sonuc, "r", encoding="utf-8") as f:
        icerik = f.read()
    return ("TOPLAM DOSYA: " + str(len(b["dosyalar"]))) in icerik


ADIMLAR = [
    {"ad": "dosyalari_listele", "yontemler": {"listele_a": listele_a, "listele_b": listele_b},
     "kontrol": kontrol_listele, "cikti": "dosyalar"},
    {"ad": "yedek_al", "yontemler": {"yedek_a": yedek_a, "yedek_b": yedek_b},
     "kontrol": kontrol_yedek, "cikti": "yedek"},
    {"ad": "turune_gore_ayir", "yontemler": {"ayir_a": ayir_a, "ayir_b": ayir_b},
     "kontrol": kontrol_ayir, "cikti": "gruplar"},
    {"ad": "csv_oku", "yontemler": {"csv_a": csv_a, "csv_b": csv_b},
     "kontrol": kontrol_csv, "cikti": "csv"},
    {"ad": "rapor_yaz", "yontemler": {"rapor_a": rapor_a, "rapor_b": rapor_b},
     "kontrol": kontrol_rapor, "cikti": "rapor"},
]


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