# Teklif Ajanı · SPEC v1 (SMB)

Küçük hizmet işletmeleri (klima servisi, temizlik, boya, tesisat) için: müşteri mesajından → iş kartı → KDV dahil teklif → hazır cevap + takip mesajları. Ek olarak: işletmenin kendi müşteri listesinden "bakım zamanı gelenler"i bulup geri arama listesi çıkarır.
Gerçek kişi/kurum verisi yok. Demo işletmesi kurgusaldır: "Serin Klima Servisi".

## Neden
Küçük işletmeler gün içinde WhatsApp'tan onlarca fiyat sorusu alıyor; teklifi elle, hesap makinesiyle, geç veriyor; takip etmiyor. Eski müşteriye bakım hatırlatması hiç yapılmıyor. Kaybedilen iş buradan geliyor.

## Parçalar
1. `web/index.html` · tek dosya, backend yok, harici script yok (her şey inline). Mobil uyumlu. Türkçe arayüz, üstte TR/EN dil düğmesi.
   - Sekme 1 "Teklif": fiyat listesinden kalem seç (veya iş kartı JSON'unu yapıştır) → miktar, opsiyonel indirim (%), yol/servis bedeli kuralı → ara toplam, KDV (%20), genel toplam. Yazdırılabilir teklif (tarih, teklif no, geçerlilik 7 gün, işletme bilgileri, kalemler, notlar). "WhatsApp cevabını kopyala" ve "Takip mesajları" (2. gün, 5. gün) metinleri.
   - Sekme 2 "Fiyat listesi": CSV yükle/düzenle; varsayılan `data/fiyat_listesi.csv`.
   - Sekme 3 "Geri arama": `data/musteriler.csv` yükle → son servis tarihi + hizmetin bakım periyodu ≥ bugün olanları listele, her biri için kişisel hatırlatma mesajı.
   - Tüm hesaplar deterministik JavaScript; aynı girdi = aynı sonuç. Para TL, iki ondalık, Türkçe biçim (1.234,50 TL).
2. `skill/teklif-ajani/SKILL.md` · AutoClaw skill: serbest müşteri mesajını (yazım hatalı, kısaltmalı, sesli mesaj dökümü olabilir) okuyup fiyat listesindeki kalem kodlarına eşleyerek iş kartı JSON'u üretir: {musteri_adi?, ilce?, kalemler:[{kod, adet}], belirsizlikler:[...], sorulacak_sorular:[...]}. Fiyat UYDURMAZ; listede olmayan iş → "liste dışı, keşif gerekli". Sonra hesabı `scripts/teklif_hesapla.py` ile (web'deki ile aynı kurallar) yapar ve teklif + mesajları üretir.
3. `scripts/teklif_hesapla.py` · web aracıyla birebir aynı hesap kuralları (test edilebilir referans).
4. `tests/mesajlar.json` · 10 gerçekçi müşteri mesajı + beklenen kalemler ve beklenen genel toplam. `tests/run_tests.py`: skill'in ürettiği iş kartlarını ve hesap sonucunu beklenenle karşılaştırır, `tests/SONUC.md` yazar (kalem isabeti, toplam isabeti, sorulan soru var mı).

## Hesap kuralları (tek doğru kaynak)
- Satır tutarı = birim fiyat (KDV hariç) × adet.
- Adet indirimi: teklifteki MONT9 + MONT18 + BAKIM adetlerinin toplamı 3 veya üzeriyse, `indirim_uygun=evet` olan TÜM kalemlerin satır tutarına %10 indirim (SOKUM dahil, ama SOKUM adedi sayıma girmez).
- Servis/yol bedeli (`YOL`) her teklife 1 kez eklenir; ara toplam (indirim sonrası, KDV hariç) 3.000 TL ve üzeriyse yol bedeli 0.
- KDV %20, indirim ve yol sonrası ara toplama uygulanır.
- Yuvarlama: her adımda kuruşa (2 ondalık), banker değil normal yuvarlama.

## Test protokolü
- Beklenen toplamlar bu spec'teki kurallarla elle hesaplandı (`tests/mesajlar.json`).
- Skill her mesajı bir kez çalıştırır; insan müdahalesi yok. Sonuç tablosu dürüstçe yazılır, başarısızlık saklanmaz.
- Belirsiz mesajlarda (ör. "kaç tane bilmiyorum") doğru davranış: tahmin değil soru sormak.
