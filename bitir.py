import json
import os
import random

HAFIZA_DOSYASI = "hafiza.json"


class Hafiza:
    """Deneyimleri dosyaya yazar ve dosyadan okur."""

    def __init__(self, dosya):
        self.dosya = dosya
        self.veri = {"deneyimler": []}
        if os.path.exists(dosya):
            with open(dosya, "r", encoding="utf-8") as f:
                self.veri = json.load(f)

    def deneyim_ekle(self, gorev, yontem, basarili):
        self.veri["deneyimler"].append(
            {"gorev": gorev, "yontem": yontem, "basarili": basarili}
        )
        with open(self.dosya, "w", encoding="utf-8") as f:
            json.dump(self.veri, f, ensure_ascii=False, indent=2)

    def istatistik(self, gorev, yontem):
        """(toplam deneme, başarılı sayısı) döndürür."""
        denemeler = [
            d for d in self.veri["deneyimler"]
            if d["gorev"] == gorev and d["yontem"] == yontem
        ]
        basarili = sum(1 for d in denemeler if d["basarili"])
        return len(denemeler), basarili


class KararMotoru:
    """Geçmiş deneyimlere bakarak yöntem seçer."""

    def __init__(self, hafiza, kesif_orani=0.2):
        self.hafiza = hafiza
        self.kesif_orani = kesif_orani

    def yontem_sec(self, gorev, yontemler):
        isimler = list(yontemler.keys())

        # 1) Hiç denenmemiş yöntem varsa önce onu dene
        denenmemis = [y for y in isimler if self.hafiza.istatistik(gorev, y)[0] == 0]
        if denenmemis:
            return random.choice(denenmemis)

        # 2) Ara sıra rastgele bir yöntem dene (yeni şeyler keşfetmek için)
        if random.random() < self.kesif_orani:
            return random.choice(isimler)

        # 3) Aksi halde en başarılı yöntemi seç
        def basari_orani(y):
            toplam, basarili = self.hafiza.istatistik(gorev, y)
            return basarili / toplam
        return max(isimler, key=basari_orani)


# ---- Deneme görevi: sayıları topla (beklenen sonuç 15) ----
def yontem_a(sayilar):
    return sum(sayilar)


def yontem_b(sayilar):
    return sum(sayilar[:-1])  # kasıtlı hata: son sayıyı unutuyor


def yontem_c(sayilar):
    toplam = 0
    for s in sayilar:
        toplam += s
    return toplam


YONTEMLER = {"yontem_a": yontem_a, "yontem_b": yontem_b, "yontem_c": yontem_c}


def main():
    hafiza = Hafiza(HAFIZA_DOSYASI)
    motor = KararMotoru(hafiza)
    gorev = "sayilari_topla"
    sayilar = [3, 5, 7]
    beklenen = 15

    print("BİTİR başladı. 15 tur denenecek.\n")
    for tur in range(1, 16):
        secilen = motor.yontem_sec(gorev, YONTEMLER)
        sonuc = YONTEMLER[secilen](sayilar)
        basarili = (sonuc == beklenen)
        hafiza.deneyim_ekle(gorev, secilen, basarili)
        durum = "BAŞARILI" if basarili else "BAŞARISIZ"
        print(f"Tur {tur:2d}: {secilen} seçildi -> sonuç {sonuc} -> {durum}")

    print("\n--- Hafızadaki toplam durum ---")
    for y in YONTEMLER:
        toplam, basarili = hafiza.istatistik(gorev, y)
        print(f"{y}: {toplam} deneme, {basarili} başarılı")


main()