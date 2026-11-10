# Teklif Ajanı (Quote Agent) · SMB

A small-business quote tool for Turkish service companies. It turns a free-form customer
message into a **job card → VAT-inclusive quote → ready WhatsApp reply + day-2/day-5
follow-ups**, and keeps a **maintenance call-back list** from the shop's own customer file.

Demo business (fictional): **Serin Klima Servisi**, an air-conditioner service in İzmir.
No real customer data is used.

**Live demo:** https://ihsansoycelik.github.io/teklif-ajani/  
Built with [AutoClaw](https://autoclaw.z.ai/) · #BuiltWithAutoClaw. I wrote the spec, the price rules and the test messages; AutoClaw built the app, the skill and the tests; I checked the results with a blind set.

## What it does

| Piece | What it is |
|---|---|
| `web/index.html` | Single-file app. No backend, no external scripts, inline CSS/JS, mobile-first. Three tabs, TR/EN toggle, printable quote, copyable messages. |
| `scripts/teklif_hesapla.py` | Reference calculator + quote/WhatsApp/follow-up text + call-back list. Testable, deterministic. |
| `skill/teklif-ajani/SKILL.md` | AutoClaw skill: free text → job card JSON (no invented prices, out-of-list work is flagged, missing quantities are asked). |
| `tests/run_tests.py` | Runs the 10 messages through the job cards and the calculator, checks JS↔Python parity and the call-back list, writes `tests/SONUC.md`. |

## Try it

**Web app** — open `web/index.html` in any browser (double-click is enough):

1. Tab **Teklif**: pick items from the price list, set quantity, optional extra discount.
   Totals update live; the travel fee disappears above 3.000 TL.
2. Paste a job card JSON into **İş kartı JSON yapıştır** → **Kalemleri doldur**:
   `{"musteri_adi":"Ayşe K.","ilce":"Karşıyaka","kalemler":[{"kod":"MONT9","adet":1}],"sorulacak_sorular":[]}`
3. **Teklifi yazdır** (A4 quote with date, quote no, 7-day validity, notes),
   **WhatsApp cevabını kopyala**, **2. gün takibi**, **5. gün takibi**.
4. Tab **Fiyat listesi**: edit prices, upload a CSV, download the current list, restore defaults.
5. Tab **Geri arama**: set "today", upload a customer CSV, get everybody whose
   `last service + maintenance period` has passed, each with a personal message.

**Python**

```bash
python3 scripts/teklif_hesapla.py --is-karti is_karti.json
python3 scripts/teklif_hesapla.py --kalemler '[{"kod":"BAKIM","adet":3}]' --tarih 2026-11-10
python3 scripts/teklif_hesapla.py --geri-arama --bugun 2026-11-10
```

**Tests**

```bash
python3 tests/run_tests.py     # writes tests/SONUC.md
```

## Calculation rules (single source of truth)

- Line amount = unit price (excl. VAT) × quantity.
- **Quantity discount**: if `MONT9 + MONT18 + BAKIM` quantities add up to **3 or more**,
  every item with `indirim_uygun=evet` gets **10% off** (SOKUM included, but its quantity
  does not count towards the 3).
- **Travel fee** (`YOL`, 400 TL) is added once per quote; it becomes **0** when the
  post-discount subtotal is **3.000 TL or more**.
- **VAT 20%** is applied to the subtotal after discounts and travel fee.
- Every step is rounded to the kuruş, half-up (not banker's rounding).
- Money is handled as integer kuruş in both implementations, so Python and JS always agree.

## Test result (2026-11-10)

- Item match: **10/10 messages**, 15/15 individual items.
- Grand-total match: **9/9** quotes (all money fields: subtotal, VAT, total, travel fee).
- Question behaviour: **10/10** — the ambiguous message (unknown number of units) got
  questions instead of a guessed quote.
- JS ↔ Python parity: **9/9** cases identical to the kuruş.
- Call-back list: **3 of 7** customers due — Müşteri D (70 days late), A (27), G (5);
  B and E are not due yet, C is not due until 2027, F's service has no maintenance period.

Full table, method note and failures (none this run): [`tests/SONUC.md`](tests/SONUC.md).

## Human check

An independent blind run on 8 fresh messages (`tests/kor_mesajlar.json`, no expected
answers in the file) scored **8/8**: seven quotes matched to the kuruş, and the one
message without a job description got questions instead of a price. The same seven
cases were re-run in the browser against `hesapla()` — identical results.

That review produced two UI fixes: the totals now show the items total *before* the
quantity discount (4.750,00 → −325,00 → 4.425,00) in both the screen summary and the
printed quote, and the notes placeholder no longer claims prices include VAT.

## Files

```
teklif-ajani/
├── web/index.html            single-file app
├── scripts/teklif_hesapla.py reference calculator + texts
├── skill/teklif-ajani/SKILL.md  AutoClaw skill (message → job card → quote)
├── tests/mesajlar.json       10 messages + expected items/totals
├── tests/is_kartlari.json    job cards produced from those messages (+ reasons)
├── tests/run_tests.py        test runner
├── tests/SONUC.md            generated test report
├── data/fiyat_listesi.csv    price list
├── data/musteriler.csv       customer file
└── docs/SPEC.md              original spec
```

## Limitations

- Prices, VAT rate and discount rate are fixed to this demo business; changing them means
  editing both the Python calculator and the JS core (marker block `CALC-CORE`).
- Message→item mapping is done by the skill (an LLM), not by a deterministic parser.
  It tolerates typos and abbreviations but is not a guarantee; out-of-list work is always
  flagged instead of priced.
- The web app stores data in `localStorage`; it is single-user, no sync, no server.
- The call-back list only applies a date rule; it does not know about appointments,
  cancellations or the technician's calendar.
- Quotes are drafts: the business must approve before sending.
