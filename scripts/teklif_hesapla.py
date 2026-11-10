#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serin Klima Servisi - teklif hesaplayıcı (referans uygulama).

web/index.html içindeki JavaScript ile BİREBİR aynı kuralları uygular.
Tüm para hesabı kuruş (tamsayı) üzerinden yapılır; böylece Python ve JS
arasında kayan nokta farkı oluşmaz. Yuvarlama: yarım yukarı (banker değil).

Kurallar (docs/SPEC.md):
  1. Satır tutarı = birim fiyat (KDV hariç) x adet.
  2. Adet indirimi: MONT9 + MONT18 + BAKIM adetleri toplamı >= 3 ise,
     indirim_uygun=evet olan TÜM kalemlere %10 indirim (SOKUM dahil,
     ama SOKUM adedi sayıma girmez).
  3. YOL her teklife 1 kez eklenir; indirim sonrası ara toplam >= 3.000 TL ise 0.
  4. KDV %20, indirim ve yol sonrası ara toplama uygulanır.
  5. Her adımda kuruşa yuvarlanır.

Kullanım:
  python3 scripts/teklif_hesapla.py --is-karti is_karti.json
  python3 scripts/teklif_hesapla.py --kalemler '[{"kod":"MONT9","adet":1}]'
  echo '{"kalemler":[{"kod":"BAKIM","adet":3}]}' | python3 scripts/teklif_hesapla.py
  python3 scripts/teklif_hesapla.py --geri-arama --bugun 2026-11-10
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIYAT_CSV = os.path.join(KOK, "data", "fiyat_listesi.csv")
MUSTERI_CSV = os.path.join(KOK, "data", "musteriler.csv")

KDV_ORANI = 20            # yüzde
ADET_INDIRIM_ORANI = 10   # yüzde
ADET_INDIRIM_KODLARI = ("MONT9", "MONT18", "BAKIM")
ADET_INDIRIM_ESIGI = 3
YOL_KODU = "YOL"
YOL_ESIGI_KURUS = 300000  # 3.000,00 TL
TEKLIF_GECERLILIK_GUN = 7

ISLETME = {
    "ad": "Serin Klima Servisi",
    "adres": "Karşıyaka / İzmir",
    "telefon": "0232 000 00 00",
    "eposta": "teklif@serinklima.example",
    "vergi": "İzmir / 0000000000",
}


# ---------------------------------------------------------------- yardımcılar
def yuvarla_kurus(deger):
    """Pozitif rasyonel değeri yarım yukarı kuruşa yuvarlar (tamsayı kuruş)."""
    return int((deger * 2 + 1) // 2) if deger >= 0 else -int((-deger * 2 + 1) // 2)


def kurus_to_tl(kurus):
    return kurus / 100.0


def tl_str(kurus):
    """123450 -> '1.234,50 TL'"""
    isaret = "-" if kurus < 0 else ""
    kurus = abs(int(kurus))
    tam, kalan = divmod(kurus, 100)
    return "%s%s,%02d TL" % (isaret, "{:,}".format(tam).replace(",", "."), kalan)


# ---------------------------------------------------------------- veri
def fiyat_listesi_oku(yol=FIYAT_CSV):
    """CSV -> {kod: {...}} (fiyatlar kuruş tamsayı)."""
    liste = {}
    with open(yol, encoding="utf-8") as f:
        for satir in csv.DictReader(f):
            kod = (satir.get("kod") or "").strip()
            if not kod:
                continue
            periyot = (satir.get("bakim_periyodu_ay") or "").strip()
            liste[kod] = {
                "kod": kod,
                "hizmet": (satir.get("hizmet") or "").strip(),
                "birim": (satir.get("birim") or "adet").strip(),
                "birim_fiyat_kurus": yuvarla_kurus(float(satir["birim_fiyat_kdv_haric"]) * 100),
                "indirim_uygun": (satir.get("indirim_uygun") or "hayir").strip().lower() == "evet",
                "bakim_periyodu_ay": int(periyot) if periyot else 0,
            }
    return liste


# ---------------------------------------------------------------- hesap
def hesapla(kalemler, fiyatlar, manuel_indirim=0):
    """Teklifi hesaplar. kalemler: [{"kod": "MONT9", "adet": 1}, ...]

    Dönen sözlük hem ekranda hem testlerde kullanılır; tüm para alanları kuruş.
    """
    kalemler = [k for k in (kalemler or []) if k.get("kod")]
    adet_toplami = 0
    for k in kalemler:
        if k["kod"] in ADET_INDIRIM_KODLARI:
            adet_toplami += int(k.get("adet") or 0)
    adet_indirimi_var = adet_toplami >= ADET_INDIRIM_ESIGI

    satirlar = []
    ara_oncesi = 0
    for k in kalemler:
        kod = k["kod"]
        if kod not in fiyatlar:
            raise ValueError("Listede olmayan kalem kodu: %s" % kod)
        f = fiyatlar[kod]
        adet = int(k.get("adet") or 0)
        if adet <= 0:
            raise ValueError("%s için adet 0'dan büyük olmalı" % kod)
        satir = f["birim_fiyat_kurus"] * adet
        indirim = 0
        if adet_indirimi_var and f["indirim_uygun"]:
            indirim = yuvarla_kurus(satir * ADET_INDIRIM_ORANI / 100.0)
        net = satir - indirim
        ara_oncesi += net
        satirlar.append({
            "kod": kod,
            "hizmet": f["hizmet"],
            "birim": f["birim"],
            "adet": adet,
            "birim_fiyat_kurus": f["birim_fiyat_kurus"],
            "satir_tutari_kurus": satir,
            "adet_indirimi_kurus": indirim,
            "net_kurus": net,
        })

    manuel_indirim = int(manuel_indirim or 0)
    manuel_tutar = yuvarla_kurus(ara_oncesi * manuel_indirim / 100.0) if manuel_indirim else 0
    ara_indirimli = ara_oncesi - manuel_tutar

    yol_kurus = 0 if ara_indirimli >= YOL_ESIGI_KURUS else fiyatlar[YOL_KODU]["birim_fiyat_kurus"]
    if any(s["kod"] == YOL_KODU for s in satirlar):
        # YOL elle eklenmişse ikinci kez eklenmez.
        yol_kurus = 0

    ara_toplam = ara_indirimli + yol_kurus
    kdv = yuvarla_kurus(ara_toplam * KDV_ORANI / 100.0)
    genel = ara_toplam + kdv

    return {
        "satirlar": satirlar,
        "adet_toplami": adet_toplami,
        "adet_indirimi_uygulandi": adet_indirimi_var,
        "adet_indirimi_orani": ADET_INDIRIM_ORANI if adet_indirimi_var else 0,
        "ara_toplam_indirim_oncesi_kurus": ara_oncesi,
        "manuel_indirim_orani": manuel_indirim,
        "manuel_indirim_kurus": manuel_tutar,
        "ara_toplam_indirimli_kurus": ara_indirimli,
        "yol_kurus": yol_kurus,
        "ara_toplam_kdv_haric_kurus": ara_toplam,
        "kdv_orani": KDV_ORANI,
        "kdv_kurus": kdv,
        "genel_toplam_kurus": genel,
        "yol_esigi_uygulandi": yol_kurus == 0 and ara_indirimli >= YOL_ESIGI_KURUS,
    }


# ---------------------------------------------------------------- metinler
def teklif_no_uret(tarih=None, sira=1):
    tarih = tarih or date.today()
    return "T%s-%02d" % (tarih.strftime("%Y%m%d"), sira)


def teklif_metni(sonuc, is_karti=None, tarih=None, teklif_no=None, notlar=None):
    tarih = tarih or date.today()
    teklif_no = teklif_no or teklif_no_uret(tarih)
    is_karti = is_karti or {}
    satirlar = []
    satirlar.append("TEKLİF  %s" % teklif_no)
    satirlar.append(ISLETME["ad"] + " · " + ISLETME["telefon"])
    satirlar.append("Tarih: %s   Geçerlilik: %d gün (%s)" % (
        tarih.strftime("%d.%m.%Y"), TEKLIF_GECERLILIK_GUN,
        (tarih + timedelta(days=TEKLIF_GECERLILIK_GUN)).strftime("%d.%m.%Y")))
    musteri = ", ".join([x for x in [is_karti.get("musteri_adi"), is_karti.get("ilce")] if x])
    if musteri:
        satirlar.append("Müşteri: " + musteri)
    satirlar.append("-" * 46)
    for s in sonuc["satirlar"]:
        satirlar.append("%-26s %2d x %8s = %10s" % (
            s["hizmet"][:26], s["adet"], tl_str(s["birim_fiyat_kurus"]), tl_str(s["satir_tutari_kurus"])))
        if s["adet_indirimi_kurus"]:
            satirlar.append("%-26s    adet indirimi     -%10s" % ("", tl_str(s["adet_indirimi_kurus"])))
    satirlar.append("-" * 46)
    satirlar.append("Ara toplam (KDV hariç): %s" % tl_str(sonuc["ara_toplam_kdv_haric_kurus"]))
    if sonuc["yol_kurus"] == 0:
        satirlar.append("Servis/yol: 0,00 TL (3.000 TL üzeri teklif)")
    satirlar.append("KDV %%%d: %s" % (sonuc["kdv_orani"], tl_str(sonuc["kdv_kurus"])))
    satirlar.append("GENEL TOPLAM: %s" % tl_str(sonuc["genel_toplam_kurus"]))
    if notlar:
        satirlar.append("-" * 46)
        for n in notlar:
            satirlar.append("Not: " + n)
    return "\n".join(satirlar)


def whatsapp_mesaji(sonuc, is_karti=None, teklif_no=None):
    is_karti = is_karti or {}
    ad = is_karti.get("musteri_adi")
    hitap = ("Merhaba %s, " % ad) if ad else "Merhaba, "
    parcalar = []
    for s in sonuc["satirlar"]:
        parcalar.append("%s x%d = %s" % (s["hizmet"], s["adet"], tl_str(s["net_kurus"])))
    metin = hitap + "teklifimiz aşağıda:\n" + "\n".join(parcalar)
    metin += "\nAra toplam (KDV hariç): %s" % tl_str(sonuc["ara_toplam_kdv_haric_kurus"])
    metin += "\nKDV %%%d dahil toplam: %s" % (sonuc["kdv_orani"], tl_str(sonuc["genel_toplam_kurus"]))
    if sonuc["yol_kurus"] == 0:
        metin += "\n(Servis/yol bedeli alınmıyor.)"
    if sonuc["adet_indirimi_uygulandi"]:
        metin += "\n(%d kalemde %%10 adet indirimi uygulandı.)" % len(
            [s for s in sonuc["satirlar"] if s["adet_indirimi_kurus"]])
    metin += "\nFiyat %d gün geçerlidir. Uygun olduğunuz günü yazın, planlayalım." % TEKLIF_GECERLILIK_GUN
    if teklif_no:
        metin += "\nTeklif no: " + teklif_no
    metin += "\n" + ISLETME["ad"]
    return metin


def takip_mesaji(gun, sonuc=None, is_karti=None, teklif_no=None):
    is_karti = is_karti or {}
    ad = is_karti.get("musteri_adi")
    hitap = ("Merhaba %s, " % ad) if ad else "Merhaba, "
    toplam = tl_str(sonuc["genel_toplam_kurus"]) if sonuc else ""
    if gun == 2:
        return (hitap + "dün gönderdiğim teklif (%s) hakkında bir sorunuz var mı? "
                "Tarih ve saat seçerseniz yerinizi ayırabilirim." % (teklif_no or "teklif")).strip()
    if gun == 5:
        return (hitap + "teklifimiz (%s) %s tutarındaydı; bu hafta için 2 müsait günümüz var. "
                "İsterseniz keşif için de uğrayabilirim. Teklif %d gün geçerli." % (
                    teklif_no or "teklif", toplam, TEKLIF_GECERLILIK_GUN)).strip()
    raise ValueError("Takip günü 2 veya 5 olmalı")


# ---------------------------------------------------------------- geri arama
def musteri_oku(yol=MUSTERI_CSV):
    satirlar = []
    with open(yol, encoding="utf-8") as f:
        for s in csv.DictReader(f):
            if (s.get("musteri") or "").strip():
                satirlar.append({
                    "musteri": s["musteri"].strip(),
                    "ilce": (s.get("ilce") or "").strip(),
                    "telefon": (s.get("telefon") or "").strip(),
                    "hizmet_kodu": (s.get("hizmet_kodu") or "").strip(),
                    "son_servis": (s.get("son_servis") or "").strip(),
                })
    return satirlar


def _ay_ekle(tarih, ay):
    yil = tarih.year + (tarih.month - 1 + ay) // 12
    ay_no = (tarih.month - 1 + ay) % 12 + 1
    gun = tarih.day
    while True:
        try:
            return date(yil, ay_no, gun)
        except ValueError:
            gun -= 1


def geri_arama(fiyatlar, musteriler, bugun=None):
    """Bakım zamanı gelen müşteriler + kişisel hatırlatma mesajı."""
    bugun = bugun or date.today()
    if isinstance(bugun, str):
        bugun = datetime.strptime(bugun, "%Y-%m-%d").date()
    gelenler, atlanan = [], []
    for m in musteriler:
        f = fiyatlar.get(m["hizmet_kodu"])
        if not f or not f.get("bakim_periyodu_ay"):
            atlanan.append(dict(m, neden="hizmetin bakım periyodu tanımlı değil"))
            continue
        try:
            son = datetime.strptime(m["son_servis"], "%Y-%m-%d").date()
        except ValueError:
            atlanan.append(dict(m, neden="son servis tarihi okunamadı"))
            continue
        vade = _ay_ekle(son, f["bakim_periyodu_ay"])
        if vade <= bugun:
            gecikme = (bugun - vade).days
            gelenler.append(dict(
                m,
                hizmet=f["hizmet"],
                periyot_ay=f["bakim_periyodu_ay"],
                vade=vade.isoformat(),
                gecikme_gun=gecikme,
                mesaj=(
                    "Merhaba %s, klimanızın periyodik bakım zamanı geldi "
                    "(son bakım %s, %s). Bu hafta müsait olduğunuz bir gün var mı? "
                    "Bakım ücreti %s." % (
                        m["musteri"], son.strftime("%d.%m.%Y"), m["ilce"],
                        tl_str(f["birim_fiyat_kurus"]))
                ).replace("  ", " "),
            ))
        else:
            atlanan.append(dict(m, neden="vade %s" % vade.isoformat()))
    gelenler.sort(key=lambda x: (-x["gecikme_gun"], x["musteri"]))
    return {"bugun": bugun.isoformat(), "gelenler": gelenler, "atlanan": atlanan}


# ---------------------------------------------------------------- CLI
def _kalemler_girdiden(args):
    if args.is_karti:
        with open(args.is_karti, encoding="utf-8") as f:
            veri = json.load(f)
    elif args.kalemler:
        veri = json.loads(args.kalemler)
    elif not sys.stdin.isatty():
        veri = json.loads(sys.stdin.read() or "{}")
    else:
        veri = {"kalemler": []}
    if isinstance(veri, list):
        veri = {"kalemler": veri}
    return veri


def main(argv=None):
    p = argparse.ArgumentParser(description="Teklif hesaplayıcı (Serin Klima Servisi)")
    p.add_argument("--is-karti", help="İş kartı JSON dosyası")
    p.add_argument("--kalemler", help="Kalemler JSON dizisi")
    p.add_argument("--indirim", type=int, default=0, help="Manuel indirim %% (0-50)")
    p.add_argument("--tarih", help="Teklif tarihi YYYY-MM-DD")
    p.add_argument("--teklif-no", help="Teklif numarası")
    p.add_argument("--geri-arama", action="store_true", help="Bakım zamanı gelenleri listele")
    p.add_argument("--bugun", help="Geri arama için bugünün tarihi YYYY-MM-DD")
    p.add_argument("--json", action="store_true", help="Sadece JSON çıktısı")
    args = p.parse_args(argv)

    fiyatlar = fiyat_listesi_oku()

    if args.geri_arama:
        sonuc = geri_arama(fiyatlar, musteri_oku(), args.bugun)
        if args.json:
            print(json.dumps(sonuc, ensure_ascii=False, indent=2))
        else:
            print("Geri arama listesi · %s · %d müşteri" % (sonuc["bugun"], len(sonuc["gelenler"])))
            for g in sonuc["gelenler"]:
                print("- %s (%s) · %s · vade %s · %d gün gecikme" % (
                    g["musteri"], g["ilce"], g["hizmet"], g["vade"], g["gecikme_gun"]))
                print("  " + g["mesaj"])
        return 0

    veri = _kalemler_girdiden(args)
    kalemler = veri.get("kalemler") or []
    if not kalemler:
        print("Kalem yok. --is-karti veya --kalemler verin.", file=sys.stderr)
        return 2

    tarih = datetime.strptime(args.tarih, "%Y-%m-%d").date() if args.tarih else date.today()
    sonuc = hesapla(kalemler, fiyatlar, veri.get("indirim", args.indirim))
    teklif_no = args.teklif_no or teklif_no_uret(tarih)
    if args.json:
        cikti = dict(sonuc)
        cikti["teklif_no"] = teklif_no
        cikti["tarih"] = tarih.isoformat()
        cikti["genel_toplam"] = kurus_to_tl(sonuc["genel_toplam_kurus"])
        print(json.dumps(cikti, ensure_ascii=False, indent=2))
        return 0
    print(teklif_metni(sonuc, veri, tarih, teklif_no, veri.get("notlar")))
    print()
    print("--- WhatsApp cevabı ---")
    print(whatsapp_mesaji(sonuc, veri, teklif_no))
    print()
    print("--- 2. gün takibi ---")
    print(takip_mesaji(2, sonuc, veri, teklif_no))
    print()
    print("--- 5. gün takibi ---")
    print(takip_mesaji(5, sonuc, veri, teklif_no))
    return 0


if __name__ == "__main__":
    sys.exit(main())
