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
<select id="gorev" onchange="gorevDegisti()">
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
function gorev(){return document.getElementById("gorev").value;}

async function durumYukle(){
  const r = await fetch("/durum?gorev=" + gorev());
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
    const s = await gonder("/yukle", {gorev: gorev(), ad: f.name, b64: b64});
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
  const s = await gonder("/yukle", {gorev: gorev(), ad: ad, icerik: icerik});
  mesaj.textContent = s.mesaj || s.hata;
  document.getElementById("yeniMetin").value = "";
  durumYukle();
}

async function gorevCalistir(){
  const g = document.getElementById("gunluk");
  g.textContent = "BİTİR çalışıyor...";
  const tur = parseInt(document.getElementById("turSayisi").value) || 1;
  const s = await gonder("/calistir", {gorev: gorev(), tur: tur});
  g.textContent = s.log;
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
            istatistik.append({"adim": adim["ad"],