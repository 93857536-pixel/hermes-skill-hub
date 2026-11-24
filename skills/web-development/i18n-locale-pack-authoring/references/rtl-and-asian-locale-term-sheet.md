# Launcher UI Term Sheet #2 — RTL + South/Southeast Asian (ar / he / fa / ur / hi / th / vi / id)

Companion to `references/launcher-ui-term-sheet.md` (zh-TW/ja/ko/de/fr/es/it/pt-BR). Same
project (CraftCraft Launcher `src/i18n/locales/`), same **81-key** contract — verified with
set+placeholder parity against `en.ts`, `tsc` clean, and all 8 native-script strings found in
`dist/assets/index-*.js` after `npm run build`. Use this to keep later batches (bn, ta, ms, fil,
az, kk…) consistent and to avoid re-deciding vocabulary.

## Four of these are RTL: ar, he, fa, ur

RTL is **registry-driven, not per-file**. In this project `src/i18n/index.tsx` already carried
`{ code: 'ar', rtl: true }`, `he`, `fa`, `ur` in `LANG_META`, and the provider does:

```ts
document.documentElement.dir = rtl ? 'rtl' : 'ltr';
```

So writing the locale files is the whole job — **check `LANG_META` before editing it**, and if
the codes are already listed with `rtl: true`, touch nothing. If a new RTL code is *not* listed,
adding the file alone ships LTR-rendered Arabic: the strings exist but every layout is mirrored
wrong. Verify by reading `LANG_META`, not by assuming.

Rules for RTL string content:

- **Native script only** — no Latin transliteration of the language name in the file header
  (`/** العربية */`, `/** עברית */`, `/** فارسی */`, `/** اردو */`) or of UI words.
- **Latin brand nouns stay Latin inside RTL text**: `CraftCraft`, `Java`, `JDK`, `Temurin`,
  `Minecraft`, `Rosetta 2`, `MB`, `x86_64`. They are bidi islands; do not wrap them in marks.
- **Placeholders keep ASCII braces**: `{n}` must not become `{n}` with Arabic-Indic digits or
  full-width braces. The interpolator is `/\\{(\\w+)\\}/g` — only ASCII `{word}` matches.
- **Leading `+` / `…` are neutral characters.** `'+ إنشاء نسخة'` and `'جارٍ التنزيل…'` render
  fine (the `+` sits on the right edge), so keep them byte-identical to `en.ts` rather than
  reordering — cosmetic position is not worth a divergence.
- **Persian half-space (ZWNJ, U+200C)** is required in `نمونه‌ها` and `گزارش‌ها`. Typing a
  normal space there is a visible typo to native readers. Copy the shipped strings verbatim.
- Do not add RTL control chars (`\\u200F`/RLM) to strings; the `dir` attribute already handles
  direction and stray marks leak into screenshots and grep checks.

## Core vocabulary (as shipped)

| en | ar | he | fa | ur |
|---|---|---|---|---|
| Instances | النسخ | מופעים | نمونه‌ها | انسٹینسز |
| New Instance | نسخة جديدة | מופע חדש | نمونهٔ جدید | نیا انسٹینس |
| Settings | الإعدادات | הגדרות | تنظیمات | ترتیبات |
| Servers | الخوادم | שרתים | سرورها | سرورز |
| Logs | السجلات | יומנים | گزارش‌ها | لاگز |
| Save | حفظ | שמירה | ذخیره | محفوظ کریں |
| Create | إنشاء | יצירה | ایجاد | بنائیں |
| Delete | حذف | מחיקה | حذف | حذف کریں |
| Launch | تشغيل | הפעלה | اجرا | چلائیں |
| Refresh | تحديث | רענון | بازخوانی | تازہ کریں |
| Loader | المحمّل | מטעין | لودر | لوڈر |
| Max Memory (MB) | أقصى ذاكرة | זיכרון מקסימלי | حداکثر حافظه | زیادہ سے زیادہ میموری |
| Java Runtime | بيئة تشغيل Java | סביבת Java | محیط اجرای Java | Java رن ٹائم |
| Installed JDKs | حزم JDK المثبّتة | חבילות JDK מותקנות | JDKهای نصب‌شده | نصب شدہ JDK |
| Vendor | المزوّد | ספק | سازنده | وینڈر |
| Arch | المعمارية | ארכיטקטורה | معماری | آرکیٹیکچر |
| address:port | العنوان:المنفذ | כתובת:פורט | نشانی:درگاه | پتہ:پورٹ |
| Online / Offline | متصل / غير متصل | מקוון / לא מקוון | آنلاین / آفلاین | آن لائن / آف لائن |

| en | hi | th | vi | id |
|---|---|---|---|---|
| Instances | इंस्टेंस | อินสแตนซ์ | Bản cài | Instans |
| New Instance | नया इंस्टेंस | อินสแตนซ์ใหม่ | Bản cài mới | Instans Baru |
| Settings | सेटिंग्स | การตั้งค่า | Cài đặt | Pengaturan |
| Servers | सर्वर | เซิร์ฟเวอร์ | Máy chủ | Server |
| Logs | लॉग | บันทึก | Nhật ký | Log |
| Save | सहेजें | บันทึก | Lưu | Simpan |
| Create | बनाएँ | สร้าง | Tạo | Buat |
| Delete | हटाएँ | ลบ | Xóa | Hapus |
| Launch | लॉन्च करें | เปิดเกม | Khởi chạy | Jalankan |
| Refresh | रीफ़्रेश | รีเฟรช | Làm mới | Muat ulang |
| Loader | लोडर | ตัวโหลด | Trình tải | Loader |
| Max Memory (MB) | अधिकतम मेमोरी | หน่วยความจำสูงสุด | Bộ nhớ tối đa | Memori Maksimum |
| Java Runtime | Java रनटाइम | รันไทม์ Java | Môi trường Java | Runtime Java |
| Installed JDKs | इंस्टॉल किए गए JDK | JDK ที่ติดตั้งแล้ว | JDK đã cài | JDK Terpasang |
| Vendor | विक्रेता | ผู้จำหน่าย | Nhà cung cấp | Vendor |
| Arch | आर्क | สถาปัตยกรรม | Kiến trúc | Arsitektur |
| address:port | पता:पोर्ट | ที่อยู่:พอร์ต | địa chỉ:cổng | alamat:port |
| Online / Offline | ऑनलाइन / ऑफ़लाइन | ออนไลน์ / ออฟไลน์ | Trực tuyến / Ngoại tuyến | Online / Offline |

## Decisions worth not re-litigating

- **`count_one` == `count_other` is CORRECT for fa, ur, th, vi, id** (and acceptable for hi).
  Persian/Urdu take a singular noun after numerals, Thai/Vietnamese/Indonesian have no plural
  inflection. Do **not** "fix" these into distinct strings — an auditor flagging them is wrong.
  Arabic and Hebrew *do* inflect (`نسخة`/`نسخ`, `מופע`/`מופעים`) and were split properly.
- **ar `النسخ`** (not `المثيلات`): the cloud-computing calque reads as "specimens" in a game
  launcher; النسخ matches what Minecraft-adjacent Arabic UIs use. Defensible either way — keep
  one and stay consistent.
- **he `יומנים`** for Logs, not `לוגים`. `לוגים` is the developer-transliterated form; the app
  shell elsewhere is native-register. If a future batch switches, switch the whole file.
- **fa uses Persian-only vocabulary** (`گزارش‌ها`, `تنظیمات`, `نمونه‌ها`), not Arabic loans
  (`سجلات`, `اعدادات`) — that is the modern Iranian software register.
- **ur keeps English tech loans** (`انسٹینسز`, `لاگز`, `سرورز`, `لوڈر`, `ٹیگ`): Urdu dev-tool
  UIs do not coin native words for these, and coinages read oddly.
- **hi `इंस्टेंस` transliterated, not `प्रतिरूप`/`संस्करण`** — Devanagari transliteration is what
  real Hindi UI ships; `संस्करण` means *version* and would collide with `wizard.version`.
- **th `เปิดเกม` for Launch** (literally "open game") beats a transliteration of "launch";
  `บันทึก` covers both Save and Logs, disambiguated by position — that is normal Thai.
- **vi `Bản cài` for instance** (installed copy). `Phiên bản` is "version" and would collide
  with `wizard.version`; `Instance` left untranslated reads as untranslated.
- **id `Instans`** — the Indonesianized spelling, not the English `Instance`.
- **`common.del` stays a stub**: `حذف` / `מחק` / `حذف` / `حذف` / `हटाएँ` / `ลบ` / `Xóa` / `Hapus`.
  One short word, no "Delete …" phrasing — the button slot is narrow in every script.
- **`java.legacyNote` carries the brand cluster** in all 8 — re-read that key specifically when
  auditing; it is where `Minecraft 1.12`, `Java 8`, `x86_64`, `Apple Silicon`, `Rosetta 2`,
  `MB` all co-occur and where a translator is most tempted to localize a product name.

## Re-running this batch's verification

```bash
# 1. parity: keys, count, placeholder sets, duplicates, empties (base = en.ts, 81 keys)
node <skill>/scripts/verify-locales.mjs src/i18n/locales en.ts

# 2. syntax: project-local compiler, not npx
./node_modules/.bin/tsc --noEmit --skipLibCheck --target es2020 \
  --moduleResolution bundler --module esnext src/i18n/locales/{ar,he,fa,ur,hi,th,vi,id}.ts

# 3. whole app, then prove the native strings actually shipped
npm run build
for s in 'النسخ' 'מופעים' 'نمونه‌ها' 'انسٹینسز' 'इंस्टेंस' 'อินสแตนซ์' 'Bản cài' 'Instans'; do
  printf '%s -> ' "$s"; grep -c "$s" dist/assets/index-*.js
done
```

Each grep must print at least 1. All-zero across the board means the eager glob did not pick the
files up (or the i18n entry is unimported) — that is a wiring finding, not a translation bug.
