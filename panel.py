import contextlib
import io
import json
import os
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from bitir import Hafiza
from ogrenen_planlayici import AkilliKararMotoru
import gercek_gorev as g

PORT = 8000
MAX_BOYUT = 1000000  # tek seferde en fazla 1 MB veri kabul edilir

SAYFA = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>BİTİR Kontrol Paneli</title>
<style>
body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:20px auto;padding:0 12px;background:#f4f5f7;color:#1c1c1c}
h1{margin-bottom:4px}
.kart{background:#fff;border-radius:8px;padding:14px 16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.12)}
button{background:#2563eb;color:#fff;border:0;padding:8px 14px;border-radius:6px;cursor:pointer;font-size:14px}
button:hover{background:#1d4ed8}
pre{background:#111;color:#e5e5e5;padding:10px;border-radius:6px;overflow:auto;white-space:pre-wrap;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:14px}
td,th{border-bottom:1px solid #ddd;padding:4px 6px;text-align:left}
input[type=text],textarea{width:100%;box-sizing:border-box;padding:6px;margin:4px 0}
.kotu{color:#b91c1c}
.iyi{color:#15803d}
.not{color:#555;font-size:13px}
</style>
</head>
<body>
<h1>BİTİR Kontrol Paneli</h1>
<div class="not">Bu sayfa yalnızca bu bilgisayarda çalışır.</div>

<div class="kart">
<h3>1. BİTİR'e dosya ver</h3>
<p>Bilgisayarınızdan bir veya birkaç .txt dosyası seçin:</p>
<input type="file" id="dosyaSecici" accept=".txt" multiple>
<button onclick="dosyalariYukle()">Seçilen dosyaları yükle</button>
<p>Ya da metni buraya yazın:</p>
<input type="text" id="yeniAd" placeholder="Dosya adı (örnek: not1.txt)">
<textarea id="yeniMetin" rows="4" placeholder="Metni buraya yazın"></textarea>
<button onclick="metniKaydet()">Metni dosya olarak kaydet</button>
<p id="yukleMesaj" class="iyi"></p>
<div><b>Şu an belgelerde olan dosyalar:</b> <span id="dosyaListesi"></span></div>
</div>

<div class="kart">
<h3>2. Görevi çalıştır</h3>
<p>Görev: belgelerdeki .txt dosyalarını bul, oku, kelimeleri say, rapor yaz.</p>
Tur sayısı: <input type="number" id="turSayisi" value="1" min="1" max="20" style="width:60px">
<button onclick="gorevCalistir()">Görevi çalıştır</button>
<pre id="gunluk">Henüz çalıştırılmadı.</pre>
</div>

<div class="kart">
<h3>3. Son rapor</h3>
<pre id="rapor">Henüz rapor yok.</pre>
</div>

<div class="kart">
<h3>4. Hafıza: yöntemler ne kadar başarılı?</h3>
<table id="tablo"></table>
</div>

<div class="kart">
<h3>5. Yasaklı yöntemler ve son hatalar</h3>
<div id="yasaklar"></div>
<p><b>Son hatalar</b> (toplam <span id="hataToplam">0</span>):</p>
<div id="hatalar"></div>
</div>

<script>
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

async function durumYukle(){
  const r = await fetch("/durum");
  const d = await r.json();
  document.getElementById("dosyaListesi").textContent = d.dosyalar.length ? d.dosyalar.join(", ") : "(henüz yok)";
  document.getElementById("rapor").textContent = d.rapor || "Henüz rapor yok.";
  let t = "<tr><th>Adım</th><th>Yöntem</th><th>Deneme</th><th>Başarılı</th></tr>";
  for (const s of d.istatistik){
    const sinif = (s.toplam > 0 && s.basarili === 0) ? "kotu" : "";
    t += "<tr class='" + sinif + "'><td>" + esc(s.adim) + "</td><td>" + esc(s.yontem) + "</td><td>" + s.toplam + "</td><td>" + s.basarili + "</td></tr>";
  }
  document.getElementById("tablo").innerHTML = t;
  let y = "";
  for (const k in d.yasaklilar){ y += "<div>" + esc(k) + ": <b>" + esc(d.yasaklilar[k].join(", ")) + "</b></div>"; }
  document.getElementById("yasaklar").innerHTML = y || "Henüz yasaklı yöntem yok.";
  document.getElementById("hataToplam").textContent = d.hata_toplam;
  let h = "";
  for (const e of d.hatalar){ h += "<div class='kotu'>" + esc(e.adim) + " / " + esc(e.yontem) + ": " + esc(e.hata) + "</div>"; }
  document.getElementById("hatalar").innerHTML = h || "Hata yok.";
}

async function gonder(adres, veri){
  const r = await fetch(adres, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(veri)});
  return await r.json();
}

async function dosyalariYukle(){
  const secici = document.getElementById("dosyaSecici");
  if (!secici.files.length){ document.getElementById("yukleMesaj").textContent = "Önce bir dosya seçin."; return; }
  let sayi = 0;
  for (const f of secici.files){
    const icerik = await f.text();
    await gonder("/yukle", {ad: f.name, icerik: icerik});
    sayi++;
  }
  document.getElementById("yukleMesaj").textContent = sayi + " dosya yüklendi.";
  secici.value = "";
  durumYukle();
}

async function metniKaydet(){
  const ad = document.getElementById("yeniAd").value;
  const icerik = document.getElementById("yeniMetin").value;
  if (!icerik.trim()){ document.getElementById("yukleMesaj").textContent = "Önce bir metin yazın."; return; }
  const s = await gonder("/yukle", {ad: ad, icerik: icerik});
  document.getElementById("yukleMesaj").textContent = s.mesaj || s.hata;
  document.getElementById("yeniMetin").value = "";
  durumYukle();
}

async function gorevCalistir(){
  const g = document.getElementById("gunluk");
  g.textContent = "BİTİR çalışıyor...";
  const tur = parseInt(document.getElementById("turSayisi").value) || 1;
  const s = await gonder("/calistir", {tur: tur});
  g.textContent = s.log;
  durumYukle();
}

durumYukle();
</script>
</body>
</html>
"""


def durum():
    hafiza = Hafiza(g.HAFIZA_DOSYASI)
    dosyalar = sorted(os.listdir(g.KLASOR)) if os.path.exists(g.KLASOR) else []
    istatistik = []
    for adim in g.ADIMLAR:
        for y in adim["yontemler"]:
            toplam, basarili = hafiza.istatistik(adim["ad"], y)
            istatistik.append({"adim": adim["ad"], "yontem": y, "toplam": toplam, "basarili": basarili})
    rapor = ""
    if os.path.exists(g.RAPOR_YOLU):
        with open(g.RAPOR_YOLU, "r", encoding="utf-8") as f:
            rapor = f.read()
    yasaklilar = {k: v for k, v in hafiza.veri.get("dersler", {}).items() if v}
    hatalar = hafiza.veri.get("hatalar", [])
    return {
        "dosyalar": dosyalar,
        "istatistik": istatistik,
        "rapor": rapor,
        "yasaklilar": yasaklilar,
        "hatalar": hatalar[-8:],
        "hata_toplam": len(hatalar),
    }


def yukle(veri):
    ad = os.path.basename(str(veri.get("ad", "")).strip())
    ad = re.sub(r"[^\w.\- ]", "_", ad)
    if not ad:
        ad = "yeni_dosya.txt"
    if not ad.lower().endswith(".txt"):
        ad += ".txt"
    icerik = str(veri.get("icerik", ""))
    os.makedirs(g.KLASOR, exist_ok=True)
    with open(os.path.join(g.KLASOR, ad), "w", encoding="utf-8") as f:
        f.write(icerik)
    return {"mesaj": "'" + ad + "' kaydedildi."}


def calistir(veri):
    os.makedirs(g.KLASOR, exist_ok=True)
    txt_var = any(a.endswith(".txt") for a in os.listdir(g.KLASOR))
    if not txt_var:
        return {"log": "Belgeler klasöründe hiç .txt dosyası yok. Önce bir dosya ekleyin."}

    try:
        tur_sayisi = int(veri.get("tur", 1))
    except (TypeError, ValueError):
        tur_sayisi = 1
    tur_sayisi = max(1, min(20, tur_sayisi))

    hafiza = Hafiza(g.HAFIZA_DOSYASI)
    motor = AkilliKararMotoru(hafiza)
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        for ders in g.ders_cikar(hafiza):
            print("DERS: " + ders + " hiç başarılı olmadı, artık denenmeyecek.")
        for tur in range(1, tur_sayisi + 1):
            print("=== GÖREV TURU " + str(tur) + " ===")
            baglam = {}
            tamam = True
            for adim in g.ADIMLAR:
                if not g.adimi_calistir(motor, hafiza, adim, baglam):
                    tamam = False
                    print("   Görev yarım kaldı!")
                    break
            if tamam:
                print("   Görev tamamlandı.")
            for ders in g.ders_cikar(hafiza):
                print("   DERS: " + ders + " hiç başarılı olmadı, artık denenmeyecek.")
    return {"log": tampon.getvalue()}


class Isleyici(BaseHTTPRequestHandler):
    def _gonder(self, kod, icerik, tur):
        veri = icerik.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def _json(self, nesne, kod=200):
        self._gonder(kod, json.dumps(nesne, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path == "/":
            self._gonder(200, SAYFA, "text/html; charset=utf-8")
        elif self.path == "/durum":
            self._json(durum())
        else:
            self._gonder(404, "Bulunamadi", "text/plain; charset=utf-8")

    def do_POST(self):
        uzunluk = int(self.headers.get("Content-Length", 0))
        if uzunluk > MAX_BOYUT:
            self._json({"hata": "Veri çok büyük (en fazla 1 MB)."}, 413)
            return
        govde = self.rfile.read(uzunluk)
        try:
            veri = json.loads(govde.decode("utf-8")) if govde else {}
        except ValueError:
            self._json({"hata": "Geçersiz veri."}, 400)
            return
        if self.path == "/yukle":
            self._json(yukle(veri))
        elif self.path == "/calistir":
            self._json(calistir(veri))
        else:
            self._json({"hata": "Bilinmeyen istek."}, 404)

    def log_message(self, *args):
        pass  # ekranı gereksiz yazılarla doldurmasın


def main():
    os.makedirs(g.KLASOR, exist_ok=True)
    adres = "http://localhost:" + str(PORT)
    sunucu = HTTPServer(("127.0.0.1", PORT), Isleyici)
    print("BİTİR paneli çalışıyor: " + adres)
    print("Kapatmak için bu pencerede Ctrl + C tuşlarına basın.")
    webbrowser.open(adres)
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel kapatıldı.")


if __name__ == "__main__":
    main()