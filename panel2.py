import base64
import contextlib
import io
import json
import os
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from bitir import Hafiza
from ogrenen_planlayici import AkilliKararMotoru
import gercek_gorev as kelime
import beceriler as klasor

PORT = 8000
MAX_BOYUT = 20000000  # tek seferde en fazla yaklaşık 20 MB veri
METIN_UZANTILARI = (".txt", ".csv", ".md", ".json", ".log", ".tsv")

GOREVLER = {
    "kelime": {
        "aciklama": "Belgeler klasöründeki .txt dosyalarını bulur, okur, kelimeleri sayar ve rapor yazar.",
        "modul": kelime,
        "klasor": kelime.KLASOR,
        "hafiza": kelime.HAFIZA_DOSYASI,
        "rapor": kelime.RAPOR_YOLU,
        "sadece_txt": True,
    },
    "klasor": {
        "aciklama": "Düzenlenecek klasördeki dosyaları listeler, yedekler, türüne göre ayırır, CSV'leri okur ve rapor yazar. Dosyalarınızı silmez, yalnızca kopyalar.",
        "modul": klasor,
        "klasor": klasor.KAYNAK,
        "hafiza": klasor.HAFIZA_DOSYASI,
        "rapor": klasor.RAPOR_YOLU,
        "sadece_txt": False,
    },
}

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
select{font-size:15px;padding:6px}
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
<h3>0. Görev seç</h3>
<select id="gorevKutusu" onchange="gorevDegisti()">
<option value="kelime">Kelime raporu</option>
<option value="klasor">Klasör düzenleme</option>
</select>
<p id="aciklama" class="not"></p>
</div>

<div class="kart">
<h3>1. BİTİR'e dosya ver</h3>
<p>Dosyalar <b id="hedefKlasor"></b> klasörüne kaydedilir. Bilgisayarınızdan bir veya birkaç dosya seçin:</p>
<input type="file" id="dosyaSecici" multiple>
<button onclick="dosyalariYukle()">Seçilen dosyaları yükle</button>
<p>Ya da metni buraya yazın:</p>
<input type="text" id="yeniAd" placeholder="Dosya adı (örnek: not1.txt)">
<textarea id="yeniMetin" rows="4" placeholder="Metni buraya yazın"></textarea>
<button onclick="metniKaydet()">Metni dosya olarak kaydet</button>
<p id="yukleMesaj" class="iyi"></p>
<div><b>Klasörde şu an olan dosyalar:</b> <span id="dosyaListesi"></span></div>
</div>

<div class="kart">
<h3>2. Görevi çalıştır</h3>
Tur sayısı: <input type="number" id="turSayisi" value="1" min="1" max="20" style="width:60px">
<button onclick="gorevCalistir()">Görevi çalıştır</button>
<pre id="gunluk">Henüz çalıştırılmadı.</pre>
</div>

<div class="kart">
<h3>3. Son rapor</h3>
<pre id="rapor">Henüz rapor yok.</pre>
<div id="klasorler" class="iyi"></div>
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
function secilenGorev(){return document.getElementById("gorevKutusu").value;}

async function durumYukle(){
  const r = await fetch("/durum?gorev=" + secilenGorev());
  const d = await r.json();
  document.getElementById("aciklama").textContent = d.aciklama;
  document.getElementById("hedefKlasor").textContent = d.klasor;
  document.getElementById("dosyaListesi").textContent = d.dosyalar.length ? d.dosyalar.join(", ") : "(henüz yok)";
  document.getElementById("rapor").textContent = d.rapor || "Henüz rapor yok.";
  document.getElementById("klasorler").textContent = d.klasorler.length ? "Oluşan düzenli klasörler: " + d.klasorler.join(", ") : "";
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

function dosyaOku(f){
  return new Promise(function(coz, red){
    const o = new FileReader();
    o.onload = function(){ coz(o.result.split(",")[1]); };
    o.onerror = function(){ red(o.error); };
    o.readAsDataURL(f);
  });
}

async function dosyalariYukle(){
  const secici = document.getElementById("dosyaSecici");
  const mesaj = document.getElementById("yukleMesaj");
  if (!secici.files.length){ mesaj.textContent = "Önce bir dosya seçin."; return; }
  let sayi = 0;
  const hatalar = [];
  for (const f of secici.files){
    const b64 = await dosyaOku(f);
    const s = await gonder("/yukle", {gorev: secilenGorev(), ad: f.name, b64: b64});
    if (s.hata){ hatalar.push(s.hata); } else { sayi++; }
  }
  mesaj.textContent = sayi + " dosya yüklendi. " + hatalar.join(" ");
  secici.value = "";
  durumYukle();
}

async function metniKaydet(){
  const ad = document.getElementById("yeniAd").value;
  const icerik = document.getElementById("yeniMetin").value;
  const mesaj = document.getElementById("yukleMesaj");
  if (!icerik.trim()){ mesaj.textContent = "Önce bir metin yazın."; return; }
  const s = await gonder("/yukle", {gorev: secilenGorev(), ad: ad, icerik: icerik});
  mesaj.textContent = s.mesaj || s.hata;
  document.getElementById("yeniMetin").value = "";
  durumYukle();
}

async function gorevCalistir(){
  const kutu = document.getElementById("gunluk");
  kutu.textContent = "BİTİR çalışıyor...";
  const tur = parseInt(document.getElementById("turSayisi").value) || 1;
  const s = await gonder("/calistir", {gorev: secilenGorev(), tur: tur});
  kutu.textContent = s.log;
  durumYukle();
}

function gorevDegisti(){
  document.getElementById("gunluk").textContent = "Henüz çalıştırılmadı.";
  document.getElementById("yukleMesaj").textContent = "";
  durumYukle();
}

durumYukle();
</script>
</body>
</html>
"""


def gorev_al(kod):
    return GOREVLER.get(kod) or GOREVLER["kelime"]


def dosya_var(gv):
    """Görev klasöründe göreve uygun en az bir dosya var mı?"""
    if not os.path.isdir(gv["klasor"]):
        return False
    for a in os.listdir(gv["klasor"]):
        if os.path.isfile(os.path.join(gv["klasor"], a)):
            if not gv["sadece_txt"] or a.lower().endswith(".txt"):
                return True
    return False


def durum(kod):
    gv = gorev_al(kod)
    mod = gv["modul"]
    hafiza = Hafiza(gv["hafiza"])

    dosyalar = []
    if os.path.isdir(gv["klasor"]):
        dosyalar = sorted(a for a in os.listdir(gv["klasor"])
                          if os.path.isfile(os.path.join(gv["klasor"], a)))

    istatistik = []
    for adim in mod.ADIMLAR:
        for y in adim["yontemler"]:
            toplam, basarili = hafiza.istatistik(adim["ad"], y)
            istatistik.append({
                "adim": adim["ad"],
                "yontem": y,
                "toplam": toplam,
                "basarili": basarili,
            })

    rapor = ""
    if os.path.exists(gv["rapor"]):
        with open(gv["rapor"], "r", encoding="utf-8") as f:
            rapor = f.read()

    klasorler = []
    if kod == "klasor":
        kok = os.path.join(klasor.CALISMA, "duzenli")
        if os.path.isdir(kok):
            for uz in sorted(os.listdir(kok)):
                yol = os.path.join(kok, uz)
                if os.path.isdir(yol):
                    klasorler.append(uz + " (" + str(len(os.listdir(yol))) + " dosya)")

    hatalar = hafiza.veri.get("hatalar", [])
    return {
        "aciklama": gv["aciklama"],
        "klasor": gv["klasor"],
        "dosyalar": dosyalar,
        "istatistik": istatistik,
        "rapor": rapor,
        "klasorler": klasorler,
        "yasaklilar": {k: v for k, v in hafiza.veri.get("dersler", {}).items() if v},
        "hatalar": hatalar[-8:],
        "hata_toplam": len(hatalar),
    }


def yukle(veri):
    gv = gorev_al(veri.get("gorev"))
    ad = os.path.basename(str(veri.get("ad", "")).strip())
    ad = re.sub(r"[^\w.\- ]", "_", ad)
    if not ad:
        ad = "yeni_dosya"
    uz = os.path.splitext(ad)[1].lower()
    if "b64" not in veri and uz == "":
        ad += ".txt"  # elle yazılan metne uzantı ekle
        uz = ".txt"
    if gv["sadece_txt"]:
        if uz == "":
            ad += ".txt"
            uz = ".txt"
        elif uz != ".txt":
            return {"hata": "'" + ad + "' alınmadı: bu görev yalnızca .txt dosyası kabul eder."}

    if "b64" in veri:
        try:
            ham = base64.b64decode(veri["b64"])
        except (ValueError, TypeError):
            return {"hata": "'" + ad + "' okunamadı."}
    else:
        ham = str(veri.get("icerik", "")).encode("utf-8")

    # Metin dosyalarını UTF-8'e çevir (Türkçe harfler bozulmasın)
    if uz in METIN_UZANTILARI:
        metin = None
        try:
            metin = ham.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                metin = ham.decode("cp1254")
            except UnicodeDecodeError:
                metin = None
        if metin is not None:
            ham = metin.encode("utf-8")

    os.makedirs(gv["klasor"], exist_ok=True)
    with open(os.path.join(gv["klasor"], ad), "wb") as f:
        f.write(ham)
    return {"mesaj": "'" + ad + "' kaydedildi."}


def calistir(veri):
    gv = gorev_al(veri.get("gorev"))
    mod = gv["modul"]
    try:
        tur_sayisi = int(veri.get("tur", 1))
    except (TypeError, ValueError):
        tur_sayisi = 1
    tur_sayisi = max(1, min(20, tur_sayisi))

    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        try:
            mod.ornek_dosyalari_hazirla()
            if not dosya_var(gv):
                print("'" + gv["klasor"] + "' klasöründe bu göreve uygun dosya yok. Önce bir dosya ekleyin.")
            else:
                hafiza = Hafiza(gv["hafiza"])
                motor = AkilliKararMotoru(hafiza)
                for ders in mod.ders_cikar(hafiza):
                    print("DERS: " + ders + " hiç başarılı olmadı, artık denenmeyecek.")
                for tur in range(1, tur_sayisi + 1):
                    print("=== GÖREV TURU " + str(tur) + " ===")
                    baglam = {}
                    tamam = True
                    for adim in mod.ADIMLAR:
                        if not kelime.adimi_calistir(motor, hafiza, adim, baglam):
                            tamam = False
                            print("   Görev yarım kaldı!")
                            break
                    if tamam:
                        print("   Görev tamamlandı.")
                    for ders in mod.ders_cikar(hafiza):
                        print("   DERS: " + ders + " hiç başarılı olmadı, artık denenmeyecek.")
        except Exception as e:
            print("Beklenmeyen hata: " + type(e).__name__ + ": " + str(e))
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
        yol = urlparse(self.path)
        if yol.path == "/":
            self._gonder(200, SAYFA, "text/html; charset=utf-8")
        elif yol.path == "/durum":
            kod = parse_qs(yol.query).get("gorev", ["kelime"])[0]
            self._json(durum(kod))
        else:
            self._gonder(404, "Bulunamadi", "text/plain; charset=utf-8")

    def do_POST(self):
        uzunluk = int(self.headers.get("Content-Length", 0))
        if uzunluk > MAX_BOYUT:
            self._json({"hata": "Dosya çok büyük (en fazla yaklaşık 14 MB)."}, 413)
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
    # Hangi klasörden çalıştırılırsa çalıştırılsın, dosyalar proje klasöründe aransın
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
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