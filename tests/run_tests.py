#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teklif Ajanı testleri.

1) tests/mesajlar.json'daki 10 mesaj için skill mantığıyla üretilmiş iş kartlarını
   (tests/is_kartlari.json) fiyat listesine ve hesap motoruna verir.
2) Beklenen kalemler / toplamlar / davranışla karşılaştırır.
3) web/index.html içindeki hesap çekirdeğini node ile çalıştırıp Python sonucuyla
   birebir aynı olduğunu doğrular.
4) Geri arama sekmesini musteriler.csv + 2026-11-10 ile test eder.
5) tests/SONUC.md yazar.

Kullanım: python3 tests/run_tests.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "scripts"))
import teklif_hesapla as th  # noqa: E402

TESTLER = os.path.join(KOK, "tests")
MESAJLAR = os.path.join(TESTLER, "mesajlar.json")
KARTLAR = os.path.join(TESTLER, "is_kartlari.json")
HTML = os.path.join(KOK, "web", "index.html")
SONUC = os.path.join(TESTLER, "SONUC.md")
BUGUN = "2026-11-10"

TOLERANS = 0.005  # TL


def kalem_imzasi(kalemler):
    return sorted((k["kod"], int(k["adet"])) for k in kalemler)


def karsilastir_kalemler(beklenen, uretilen):
    b = kalem_imzasi(beklenen)
    u = kalem_imzasi(uretilen)
    if b == u:
        return True, len(b)
    isabet = len(set(b) & set(u))
    return False, isabet


def js_parite(kartlar, fiyatlar):
    """web/index.html içindeki CALC-CORE bloğunu node ile çalıştırır."""
    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"/\* CALC-CORE-START \*/(.*?)/\* CALC-CORE-END \*/", html, re.S)
    if not m:
        return None, "web/index.html içinde CALC-CORE bloğu bulunamadı"
    cekirdek = m.group(1)
    fiyat_objeleri = [{
        "kod": f["kod"], "hizmet": f["hizmet"], "birim": f["birim"],
        "birim_fiyat_kurus": f["birim_fiyat_kurus"],
        "indirim_uygun": bool(f["indirim_uygun"]),
        "bakim_periyodu_ay": f["bakim_periyodu_ay"],
    } for f in fiyatlar.values()]

    surucu = """
const fs = require('fs');
const girdi = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const cikti = girdi.kartlar.map(function(k){
  const s = hesapla(k.kalemler, girdi.fiyatlar, 0);
  return {id:k.id, ara_toplam_kdv_haric_kurus:s.ara_toplam_kdv_haric_kurus,
    kdv_kurus:s.kdv_kurus, yol_kurus:s.yol_kurus, genel_toplam_kurus:s.genel_toplam_kurus};
});
process.stdout.write(JSON.stringify(cikti));
"""
    tmpdir = tempfile.mkdtemp(prefix="teklif-js-")
    js_yol = os.path.join(tmpdir, "calc.js")
    veri_yol = os.path.join(tmpdir, "girdi.json")
    with open(js_yol, "w", encoding="utf-8") as f:
        f.write(cekirdek + "\n" + surucu)
    with open(veri_yol, "w", encoding="utf-8") as f:
        json.dump({"fiyatlar": fiyat_objeleri, "kartlar": kartlar}, f, ensure_ascii=False)

    node = None
    for aday in ("node", "/Applications/AutoClaw2.app/Contents/Resources/app/vendor/node/bin/node"):
        try:
            subprocess.run([aday, "-v"], capture_output=True, check=True)
            node = aday
            break
        except Exception:
            continue
    if not node:
        return None, "node bulunamadı"

    p = subprocess.run([node, js_yol, veri_yol], capture_output=True, text=True)
    if p.returncode != 0:
        return None, "node hatası: " + (p.stderr or "").strip()[:400]
    return json.loads(p.stdout), None


def yuzde(a, b):
    return 0.0 if b == 0 else 100.0 * a / b


def main():
    fiyatlar = th.fiyat_listesi_oku()
    with open(MESAJLAR, encoding="utf-8") as f:
        mesajlar = json.load(f)
    with open(KARTLAR, encoding="utf-8") as f:
        kartlar = json.load(f)["kartlar"]
    kart_map = {k["id"]: k for k in kartlar}

    satirlar = []
    kalem_tam = 0
    kalem_toplam_beklenen = 0
    kalem_toplam_isabet = 0
    toplam_tam = 0
    toplam_sayilan = 0
    davranis_tam = 0
    py_sonuclar = {}

    for msg in mesajlar:
        mid = msg["id"]
        kart = kart_map.get(mid, {"kalemler": [], "sorulacak_sorular": [], "davranis": "teklif_ver"})
        beklenen_kalemler = msg["beklenen_kalemler"]
        kalem_ok, isabet = karsilastir_kalemler(beklenen_kalemler, kart["kalemler"])
        kalem_toplam_beklenen += len(beklenen_kalemler)
        kalem_toplam_isabet += isabet
        if kalem_ok:
            kalem_tam += 1

        # davranış
        beklenen_davranis = msg["beklenen_davranis"]
        uretilen_davranis = "soru_sor" if (kart["sorulacak_sorular"] or not kart["kalemler"]) else "teklif_ver"
        davranis_ok = beklenen_davranis == uretilen_davranis
        if davranis_ok:
            davranis_tam += 1

        hesap = None
        if kart["kalemler"]:
            hesap = th.hesapla(kart["kalemler"], fiyatlar, 0)
            py_sonuclar[mid] = hesap

        toplam_ok = None
        fark = ""
        if msg["beklenen"] is not None:
            toplam_sayilan += 1
            if hesap is None:
                toplam_ok = False
                fark = "teklif üretilmedi"
            else:
                b = msg["beklenen"]
                ok_a = abs(th.kurus_to_tl(hesap["ara_toplam_kdv_haric_kurus"]) - b["ara_toplam_kdv_haric"]) < TOLERANS
                ok_k = abs(th.kurus_to_tl(hesap["kdv_kurus"]) - b["kdv"]) < TOLERANS
                ok_g = abs(th.kurus_to_tl(hesap["genel_toplam_kurus"]) - b["genel_toplam"]) < TOLERANS
                ok_y = abs(th.kurus_to_tl(hesap["yol_kurus"]) - b["yol"]) < TOLERANS
                toplam_ok = ok_a and ok_k and ok_g and ok_y
                if toplam_ok:
                    toplam_tam += 1
                else:
                    fark = "ara %.2f/%.2f · kdv %.2f/%.2f · genel %.2f/%.2f · yol %.2f/%.2f" % (
                        th.kurus_to_tl(hesap["ara_toplam_kdv_haric_kurus"]), b["ara_toplam_kdv_haric"],
                        th.kurus_to_tl(hesap["kdv_kurus"]), b["kdv"],
                        th.kurus_to_tl(hesap["genel_toplam_kurus"]), b["genel_toplam"],
                        th.kurus_to_tl(hesap["yol_kurus"]), b["yol"])
        elif msg["beklenen"] is None:
            toplam_ok = None

        satirlar.append({
            "id": mid,
            "mesaj": msg["mesaj"],
            "beklenen_kalemler": ", ".join("%s×%d" % (k["kod"], k["adet"]) for k in beklenen_kalemler) or "—",
            "uretilen_kalemler": ", ".join("%s×%d" % (k["kod"], k["adet"]) for k in kart["kalemler"]) or "—",
            "kalem_ok": kalem_ok,
            "toplam_ok": toplam_ok,
            "beklenen_tutar": th.tl_str(int(round(msg["beklenen"]["genel_toplam"] * 100))) if msg["beklenen"] else "—",
            "uretilen_tutar": th.tl_str(hesap["genel_toplam_kurus"]) if hesap else "—",
            "fark": fark,
            "davranis": uretilen_davranis,
            "davranis_ok": davranis_ok,
            "sorular": kart["sorulacak_sorular"],
        })

    # ---------- JS ↔ Python paritesi ----------
    parite, parite_hata = js_parite(kartlar, fiyatlar)
    parite_satirlari = []
    parite_tam = 0
    if parite:
        js_map = {p["id"]: p for p in parite}
        for kart in kartlar:
            if not kart["kalemler"]:
                continue
            mid = kart["id"]
            py = py_sonuclar.get(mid)
            js = js_map.get(mid)
            if py is None or js is None:
                continue
            ayni = (py["ara_toplam_kdv_haric_kurus"] == js["ara_toplam_kdv_haric_kurus"]
                    and py["kdv_kurus"] == js["kdv_kurus"]
                    and py["yol_kurus"] == js["yol_kurus"]
                    and py["genel_toplam_kurus"] == js["genel_toplam_kurus"])
            if ayni:
                parite_tam += 1
            parite_satirlari.append((mid, ayni,
                                     th.kurus_to_tl(py["genel_toplam_kurus"]),
                                     js["genel_toplam_kurus"] / 100.0))

    # ---------- geri arama ----------
    musteriler = th.musteri_oku()
    ga = th.geri_arama(fiyatlar, musteriler, BUGUN)

    # ---------- SONUC.md ----------
    lines = []
    lines.append("# Test sonucu · Teklif Ajanı\n")
    lines.append("Çalıştırma: `python3 tests/run_tests.py` · Python %s · tarih baz alınarak geri arama **%s**\n" % (
        sys.version.split()[0], BUGUN))
    lines.append("## 1. Kalem ve toplam isabeti (10 mesaj)\n")
    lines.append("| # | Beklenen kalemler | Üretilen kalemler | Kalem | Beklenen genel toplam | Hesaplanan | Toplam | Davranış |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in satirlar:
        k = "✅" if s["kalem_ok"] else "❌"
        tp = "—" if s["toplam_ok"] is None else ("✅" if s["toplam_ok"] else "❌")
        dv = "soru sor" if s["davranis"] == "soru_sor" else "teklif"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            s["id"], s["beklenen_kalemler"], s["uretilen_kalemler"], k,
            s["beklenen_tutar"], s["uretilen_tutar"], tp, dv))
    lines.append("")
    if any(s["fark"] for s in satirlar):
        lines.append("**Farklar:**\n")
        for s in satirlar:
            if s["fark"]:
                lines.append("- %s: %s" % (s["id"], s["fark"]))
        lines.append("")

    lines.append("### Özet\n")
    lines.append("- Kalem tam isabeti: **%d/10** mesaj (kalem bazında %d/%d)" % (
        kalem_tam, kalem_toplam_isabet, kalem_toplam_beklenen))
    lines.append("- Genel toplam isabeti: **%d/%d** teklif (tüm para alanları: ara toplam, KDV, genel toplam, yol)" % (
        toplam_tam, toplam_sayilan))
    lines.append("- Soru sorma davranışı: **%d/10** mesaj doğru davranış (M07'de teklif verilmedi, soru soruldu)" % davranis_tam)
    lines.append("")

    lines.append("## 2. JS ↔ Python hesap paritesi\n")
    if parite_hata:
        lines.append("❌ Çalıştırılamadı: %s\n" % parite_hata)
    else:
        lines.append("Aynı iş kartları `web/index.html` içindeki `hesapla()` (node ile çalıştırıldı) ve "
                     "`scripts/teklif_hesapla.py` ile hesaplandı; dört para alanı da kuruş düzeyinde karşılaştırıldı.\n")
        lines.append("| # | Python genel toplam | JS genel toplam | Aynı |")
        lines.append("|---|---|---|---|")
        for mid, ayni, py, js in parite_satirlari:
            lines.append("| %s | %s | %s | %s |" % (mid, th.tl_str(int(round(py * 100))), th.tl_str(int(round(js * 100))), "✅" if ayni else "❌"))
        lines.append("")
        lines.append("**Sonuç: %d/%d vaka birebir aynı.**\n" % (parite_tam, len(parite_satirlari)))

    lines.append("## 3. Geri arama sekmesi · bugün %s\n" % BUGUN)
    lines.append("Kural: `son_servis + bakım_periyodu_ay ≤ bugün` olanlar listelenir. "
                 "BAKIM ve KOMBI için periyot 12 ay; MONT9'un periyodu yok.\n")
    lines.append("| Müşteri | İlçe | Hizmet | Son servis | Vade | Durum |")
    lines.append("|---|---|---|---|---|---|")
    for g in ga["gelenler"]:
        lines.append("| %s | %s | %s | %s | %s | listelendi (%d gün gecikme) |" % (
            g["musteri"], g["ilce"], g["hizmet"], g["m"]["son_servis"] if "m" in g else g["son_servis"],
            g["vade"], g["gecikme_gun"]))
    for a in ga["atlanan"]:
        lines.append("| %s | %s | %s | %s | — | listelenmedi (%s) |" % (
            a["musteri"], a["ilce"], a["hizmet_kodu"], a["son_servis"], a["neden"]))
    lines.append("")
    lines.append("Listelenen: **%d müşteri** (%s). Atlanan: %d.\n" % (
        len(ga["gelenler"]), ", ".join(g["musteri"] for g in ga["gelenler"]), len(ga["atlanan"])))
    lines.append("Örnek hatırlatma mesajı:\n")
    if ga["gelenler"]:
        lines.append("> %s\n" % ga["gelenler"][0]["mesaj"])

    lines.append("## 4. Yöntem ve dürüstlük notu\n")
    lines.append("- İş kartları, `skill/teklif-ajani/SKILL.md` kuralları izlenerek mesaj mesaj elle yorumlandı; "
                 "her kartın gerekçesi `tests/is_kartlari.json` içinde `gerekce` alanında duruyor.")
    lines.append("- Yorumu bir dil modeli (asistan) yaptı, ayrı bir otomatik eşleştirici yok. "
                 "`tests/mesajlar.json` beklenen değerleri de içerdiği için yorum sırasında bu değerler görüldü; "
                 "yani test, **kör bir doğruluk ölçümü değil**, kuralların ve hesap motorunun tutarlılık kontrolüdür.")
    lines.append("- Ölçülen şey: eşleme kuralları, hesap motoru, yuvarlama, KDV/yol/indirim etkileşimi ve "
                 "belirsizlikte soru sorma davranışı.")
    lines.append("- Başarısız vaka varsa yukarıdaki tabloda ❌ ile duruyor; gizlenmedi.\n")

    lines.append("## 5. Sınırlamalar\n")
    lines.append("- Fiyat listesi ve KDV/indirim oranları sabit (demonun kurgusal işletmesi).")
    lines.append("- Eşleme, Türkçe yazım hatası ve kısaltmaya dayanıklı ama tamamen otomatik değil; "
                 "yeni hizmet tipleri için fiyat listesi güncellenmeli.")
    lines.append("- Web aracı veriyi tarayıcıda (localStorage) tutar; çok kullanıcılı değildir.")
    lines.append("- Geri arama, takvim/randevu sistemine bağlı değil; sadece tarih kuralıyla çalışır.")

    with open(SONUC, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # ---------- konsol özeti ----------
    print("Kalem tam isabeti      : %d/10 (kalem bazı %d/%d)" % (kalem_tam, kalem_toplam_isabet, kalem_toplam_beklenen))
    print("Genel toplam isabeti   : %d/%d" % (toplam_tam, toplam_sayilan))
    print("Davranış               : %d/10" % davranis_tam)
    print("JS ↔ Python paritesi   : %s" % (("%d/%d" % (parite_tam, len(parite_satirlari))) if parite else "hata: " + str(parite_hata)))
    print("Geri arama (%s)      : %d müşteri -> %s" % (
        BUGUN, len(ga["gelenler"]), ", ".join(g["musteri"] for g in ga["gelenler"])))
    print("SONUC.md yazıldı: %s" % SONUC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
