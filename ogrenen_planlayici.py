import json
from bitir import Hafiza, KararMotoru
from planlayici import ADIMLAR, HAFIZA_DOSYASI, adimi_calistir

MIN_DENEME = 3  # bu kadar denemeden sonra hiç başarı yoksa yöntem yasaklanır


def kaydet(hafiza):
    with open(hafiza.dosya, "w", encoding="utf-8") as f:
        json.dump(hafiza.veri, f, ensure_ascii=False, indent=2)


def hata_turu(hata):
    return hata.split(":")[0]


def hata_raporu(hafiza):
    """Hataları gruplayıp hangi yöntemin hangi hatayı kaç kez verdiğini yazar."""
    sayac = {}
    for h in hafiza.veri.get("hatalar", []):
        anahtar = (h["adim"], h["yontem"], hata_turu(h["hata"]))
        sayac[anahtar] = sayac.get(anahtar, 0) + 1

    print("\n--- HATA RAPORU ---")
    if not sayac:
        print("Kayıtlı hata yok.")
    for (adim, yontem, tur), adet in sorted(sayac.items(), key=lambda x: -x[1]):
        print(str(adet) + " kez: " + adim + " / " + yontem + " -> " + tur)


def ders_cikar(hafiza):
    """Hiç başarılı olmamış yöntemleri yasaklı listesine ekler. Yeni dersleri döndürür."""
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


class AkilliKararMotoru(KararMotoru):
    """Eski karar motoru + öğrenilmiş derslere uyar."""

    def yontem_sec(self, gorev, yontemler):
        yasaklar = self.hafiza.veri.get("dersler", {}).get(gorev, [])
        izinli = {ad: f for ad, f in yontemler.items() if ad not in yasaklar}
        if not izinli:  # hepsi yasaklıysa mecburen hepsinden seç
            izinli = yontemler
        return super().yontem_sec(gorev, izinli)


def main():
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


if __name__ == "__main__":
    main()