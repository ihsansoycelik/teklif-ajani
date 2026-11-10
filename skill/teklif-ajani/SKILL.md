---
name: teklif-ajani
description: SMB quote agent for small Turkish service businesses (klima servisi, temizlik, boya, tesisat). Turns a free-form customer message (typos, abbreviations, voice-note transcripts) into a job card JSON mapped to price-list codes, then a VAT-inclusive quote plus WhatsApp reply, day-2/day-5 follow-ups and a maintenance call-back list. Never invents prices; anything not in the price list is "liste dışı, keşif gerekli"; missing quantities are asked, not guessed. Use when a customer asks "ne kadar / fiyat / teklif", sends a job description over WhatsApp, or when the business wants a quote, follow-up messages or a bakım hatırlatma listesi.
---

# Teklif Ajanı

Küçük hizmet işletmesi (varsayılan demo: **Serin Klima Servisi**) için müşteri mesajı → iş kartı → KDV dahil teklif → hazır cevap ve takip mesajları.

## 0. Değişmez kurallar

1. **Fiyat uydurma yok.** Tek fiyat kaynağı `data/fiyat_listesi.csv` (veya işletmenin kendi listesi). Listede olmayan iş → `"liste dışı, keşif gerekli"`, fiyat verilmez.
2. **Tahmin yok.** Adet/ölçü/belirsizlik varsa `sorulacak_sorular` doldurulur, teklif kesinleştirilmez.
3. **Tek hesap kaynağı** `scripts/teklif_hesapla.py`; web aracı (`web/index.html`) aynı kuralları uygular. Elle hesap yapılmaz.
4. Mesajda olmayan bilgi (müşteri adı, ilçe) uydurulmaz; boş bırakılır.
5. Yanıt kısa ve müşterinin diliyle; fiyatlar TL, iki ondalık, `1.234,50 TL` biçiminde.

## 1. Girdi

Serbest metin: WhatsApp mesajı, sesli mesaj dökümü, eksik yazım ("2 klima bakim karsiyaka"), kısaltma ("btu", "klima", "montaj", "söküm").
Gerekirse `data/fiyat_listesi.csv` okunur; kodlar ve birimler oradan alınır.

## 2. İş kartı üret (tek çıktı: JSON)

```json
{
  "musteri_adi": "Ayşe K.",
  "ilce": "Karşıyaka",
  "kalemler": [{"kod": "MONT9", "adet": 1}],
  "belirsizlikler": ["Boru ihtiyacı 'olabilir' denmiş; keşifte kesinleşir"],
  "sorulacak_sorular": ["Kaç adet klima bakımı istiyorsunuz?"]
}
```

Kurallar:
- `kalemler` yalnız fiyat listesindeki kodlardan; `adet` pozitif tam sayı.
- `YOL` kalem olarak **eklenmez**; hesap motoru gerekliyse kendisi ekler.
- `belirsizlikler` = teklifi etkileyen ama teklifi durdurmayan notlar.
- `sorulacak_sorular` = teklif için zorunlu eksik bilgi. Dolu ise teklif **verilmez**, önce soru sorulur.

### Eşleme kılavuzu (klima)

| Mesajda geçen | Kod | Not |
|---|---|---|
| montaj/takma + 9.000–12.000 BTU ("9 bin", "12000") | `MONT9` | BTU yazılmamışsa ve tek klima ise sor |
| montaj + 18.000–24.000 BTU ("18 bin", "24lük") | `MONT18` | |
| sökme/demontaj | `SOKUM` | Söküm adedi indirim sayımına girmez |
| bakım/temizlik | `BAKIM` | "3 oda" → 3 adet |
| gaz dolumu | `GAZ` | Yalnız müşteri isterse; arıza tespitinde peşin eklenmez |
| ek boru | `BORU` | Montajda 3 m dahil → "5 metre" = 2 metre ek |
| kombi bakımı | `KOMBI` | |
| "soğutmuyor / bakmıyor / ses yapıyor" | `ARIZA` | Teşhis öncesi gaz/parça eklenmez |
| liste dışı (çatı tamiri, boya, tesisat...) | — | "liste dışı, keşif gerekli" |

Söküm + takma aynı mesajda → iki kalem birden. "Eski evden sök, yeni eve tak" → `SOKUM` + `MONT*`.

## 3. Hesap

```bash
python3 scripts/teklif_hesapla.py --is-karti is_karti.json
python3 scripts/teklif_hesapla.py --kalemler '[{"kod":"BAKIM","adet":3}]' --tarih 2026-11-10
```

Kurallar (tek doğru kaynak, `docs/SPEC.md`):
- Satır = birim fiyat (KDV hariç) × adet.
- `MONT9 + MONT18 + BAKIM` adedi ≥ 3 → `indirim_uygun=evet` tüm kalemlerde %10 (SOKUM dahil, adedi sayılmaz).
- `YOL` teklife 1 kez; indirim sonrası ara toplam ≥ 3.000 TL ise 0.
- KDV %20, indirim ve yol sonrası ara toplama.
- Her adım kuruşa, yarım yukarı yuvarlanır.

## 4. Çıktı

1. **Teklif metni**: teklif no, tarih, 7 gün geçerlilik, kalemler, ara toplam, KDV, genel toplam, notlar.
2. **WhatsApp cevabı**: kısa, kalem kalem, toplam tek satır, "fiyat 7 gün geçerli" + randevu sorusu.
3. **2. gün takibi**: nazik hatırlatma, soru var mı.
4. **5. gün takibi**: toplam + bu hafta 2 müsait gün + keşif teklifi.
5. **Geri arama listesi** (istenirse): `python3 scripts/teklif_hesapla.py --geri-arama --bugun 2026-11-10`.

Web aracı: `web/index.html` (tek dosya, tarayıcıda açılır). İş kartı JSON'u "İş kartı JSON yapıştır" alanına yapıştırınca kalemler dolar.

## 5. Kalite kontrol (teslim öncesi)

- [ ] Her kalem kodu fiyat listesinde var mı?
- [ ] Adetler mesajla uyumlu mu (3 oda → 3 bakım)?
- [ ] Boru "ek metre" olarak mı alındı (3 m dahil)?
- [ ] Listede olmayan iş için fiyat verilmedi mi?
- [ ] Eksik bilgi varsa teklif yerine soru soruldu mu?
- [ ] Toplam `teklif_hesapla.py` çıktısıyla birebir aynı mı?

## 6. Sınırlar

- Fiyat listesi dışında bilgi (stok, süre, garanti) uydurulmaz; işletmeye sorulur.
- KDV oranı ve indirim oranı sabittir; değişecekse `scripts/teklif_hesapla.py` ve `web/index.html` birlikte güncellenir.
- Teklif hukuki bağlayıcılık taşımaz; işletme onayı gerekir.
