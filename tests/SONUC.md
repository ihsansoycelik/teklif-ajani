# Test sonucu · Teklif Ajanı

Çalıştırma: `python3 tests/run_tests.py` · Python 3.9.6 · tarih baz alınarak geri arama **2026-11-10**

## 1. Kalem ve toplam isabeti (10 mesaj)

| # | Beklenen kalemler | Üretilen kalemler | Kalem | Beklenen genel toplam | Hesaplanan | Toplam | Davranış |
|---|---|---|---|---|---|---|---|
| M01 | MONT9×1 | MONT9×1 | ✅ | 2.640,00 TL | 2.640,00 TL | ✅ | teklif |
| M02 | BAKIM×3 | BAKIM×3 | ✅ | 2.586,00 TL | 2.586,00 TL | ✅ | teklif |
| M03 | SOKUM×2, MONT9×2, BORU×2 | SOKUM×2, MONT9×2, BORU×2 | ✅ | 6.840,00 TL | 6.840,00 TL | ✅ | teklif |
| M04 | ARIZA×1 | ARIZA×1 | ✅ | 1.080,00 TL | 1.080,00 TL | ✅ | teklif |
| M05 | KOMBI×1, BAKIM×1 | KOMBI×1, BAKIM×1 | ✅ | 2.340,00 TL | 2.340,00 TL | ✅ | teklif |
| M06 | MONT18×4 | MONT18×4 | ✅ | 10.368,00 TL | 10.368,00 TL | ✅ | teklif |
| M07 | — | — | ✅ | — | — | — | soru sor |
| M08 | SOKUM×1 | SOKUM×1 | ✅ | 1.320,00 TL | 1.320,00 TL | ✅ | teklif |
| M09 | MONT18×1, BORU×4, GAZ×1 | MONT18×1, BORU×4, GAZ×1 | ✅ | 6.360,00 TL | 6.360,00 TL | ✅ | teklif |
| M10 | BAKIM×2, KOMBI×1 | BAKIM×2, KOMBI×1 | ✅ | 3.120,00 TL | 3.120,00 TL | ✅ | teklif |

### Özet

- Kalem tam isabeti: **10/10** mesaj (kalem bazında 15/15)
- Genel toplam isabeti: **9/9** teklif (tüm para alanları: ara toplam, KDV, genel toplam, yol)
- Soru sorma davranışı: **10/10** mesaj doğru davranış (M07'de teklif verilmedi, soru soruldu)

## 2. JS ↔ Python hesap paritesi

Aynı iş kartları `web/index.html` içindeki `hesapla()` (node ile çalıştırıldı) ve `scripts/teklif_hesapla.py` ile hesaplandı; dört para alanı da kuruş düzeyinde karşılaştırıldı.

| # | Python genel toplam | JS genel toplam | Aynı |
|---|---|---|---|
| M01 | 2.640,00 TL | 2.640,00 TL | ✅ |
| M02 | 2.586,00 TL | 2.586,00 TL | ✅ |
| M03 | 6.840,00 TL | 6.840,00 TL | ✅ |
| M04 | 1.080,00 TL | 1.080,00 TL | ✅ |
| M05 | 2.340,00 TL | 2.340,00 TL | ✅ |
| M06 | 10.368,00 TL | 10.368,00 TL | ✅ |
| M08 | 1.320,00 TL | 1.320,00 TL | ✅ |
| M09 | 6.360,00 TL | 6.360,00 TL | ✅ |
| M10 | 3.120,00 TL | 3.120,00 TL | ✅ |

**Sonuç: 9/9 vaka birebir aynı.**

## 3. Geri arama sekmesi · bugün 2026-11-10

Kural: `son_servis + bakım_periyodu_ay ≤ bugün` olanlar listelenir. BAKIM ve KOMBI için periyot 12 ay; MONT9'un periyodu yok.

| Müşteri | İlçe | Hizmet | Son servis | Vade | Durum |
|---|---|---|---|---|---|
| Müşteri D | Konak | Klima periyodik bakım ve temizlik | 2025-09-01 | 2026-09-01 | listelendi (70 gün gecikme) |
| Müşteri A | Karşıyaka | Klima periyodik bakım ve temizlik | 2025-10-14 | 2026-10-14 | listelendi (27 gün gecikme) |
| Müşteri G | Karabağlar | Klima periyodik bakım ve temizlik | 2025-11-05 | 2026-11-05 | listelendi (5 gün gecikme) |
| Müşteri B | Bornova | KOMBI | 2025-11-30 | — | listelenmedi (vade 2026-11-30) |
| Müşteri C | Buca | BAKIM | 2026-06-02 | — | listelenmedi (vade 2027-06-02) |
| Müşteri E | Çiğli | KOMBI | 2026-01-20 | — | listelenmedi (vade 2027-01-20) |
| Müşteri F | Bayraklı | MONT9 | 2025-07-11 | — | listelenmedi (hizmetin bakım periyodu tanımlı değil) |

Listelenen: **3 müşteri** (Müşteri D, Müşteri A, Müşteri G). Atlanan: 4.

Örnek hatırlatma mesajı:

> Merhaba Müşteri D, klimanızın periyodik bakım zamanı geldi (son bakım 01.09.2025, Konak). Bu hafta müsait olduğunuz bir gün var mı? Bakım ücreti 650,00 TL.

## 4. Yöntem ve dürüstlük notu

- İş kartları, `skill/teklif-ajani/SKILL.md` kuralları izlenerek mesaj mesaj elle yorumlandı; her kartın gerekçesi `tests/is_kartlari.json` içinde `gerekce` alanında duruyor.
- Yorumu bir dil modeli (asistan) yaptı, ayrı bir otomatik eşleştirici yok. `tests/mesajlar.json` beklenen değerleri de içerdiği için yorum sırasında bu değerler görüldü; yani test, **kör bir doğruluk ölçümü değil**, kuralların ve hesap motorunun tutarlılık kontrolüdür.
- Ölçülen şey: eşleme kuralları, hesap motoru, yuvarlama, KDV/yol/indirim etkileşimi ve belirsizlikte soru sorma davranışı.
- Başarısız vaka varsa yukarıdaki tabloda ❌ ile duruyor; gizlenmedi.

## 5. Sınırlamalar

- Fiyat listesi ve KDV/indirim oranları sabit (demonun kurgusal işletmesi).
- Eşleme, Türkçe yazım hatası ve kısaltmaya dayanıklı ama tamamen otomatik değil; yeni hizmet tipleri için fiyat listesi güncellenmeli.
- Web aracı veriyi tarayıcıda (localStorage) tutar; çok kullanıcılı değildir.
- Geri arama, takvim/randevu sistemine bağlı değil; sadece tarih kuralıyla çalışır.

## 6. Kör test (beklenen cevap dosyada yoktu)

`tests/kor_mesajlar.json` içindeki 8 mesaj, `tests/kor_sonuclar.json` üretilirken tek geçişte yorumlandı; beklenen değerler ne dosyada ne de asistanın elindeydi. Düzeltme turu yapılmadı.

| # | Kalemler | Genel toplam | Davranış |
|---|---|---|---|
| B1 | MONT9×3 | 5.832,00 TL | teklif |
| B2 | SOKUM×1, BAKIM×1 | 2.100,00 TL | teklif |
| B3 | KOMBI×1, ARIZA×1 | 2.160,00 TL | teklif |
| B4 | MONT18×2 | 5.760,00 TL | teklif |
| B5 | BAKIM×5, GAZ×1 | 5.310,00 TL | teklif |
| B6 | — | — | soru sor |
| B7 | SOKUM×1, MONT9×1 | 3.480,00 TL | teklif |
| B8 | KOMBI×2 | 2.640,00 TL | teklif |

**İnsan kontrolü: 8/8 doğru.** 7 teklif kuruşu kuruşuna tuttu, 1 mesajda (B6) teklif yerine soru soruldu. Aynı 7 vaka `web/index.html` içindeki `hesapla()` ile tarayıcıda da çalıştırıldı, sonuçlar aynı.

**B4 notu:** "toplam 6 metre boru" ifadesinde soru sormak yerine, montajda 3+3 m borunun dahil olduğu varsayımı yazıldı ve alternatif belirtildi: 6 m **ek** boru kastediliyorsa 2.100,00 TL (KDV hariç) fark eder. Teklif yine de verildi çünkü eksik olan adet değil, borunun dahil mi ek mi olduğuydu.

