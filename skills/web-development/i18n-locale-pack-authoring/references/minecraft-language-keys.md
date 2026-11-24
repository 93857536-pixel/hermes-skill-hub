# `instances.language*` block — verified renderings

The 5-key block inserted immediately **after** `'instances.newCard'`, fixed order, no blank
lines between them:

| key | English base |
|---|---|
| `instances.languageAuto` | `Game language: follow game` |
| `instances.language` | `Game language` |
| `instances.languageCommon` | `Common languages` |
| `instances.languageMore` | `More languages (incl. Klingon, Quenya, toki pona…)` |
| `instances.languageDesc` | `Minecraft in-game language — passed to the game as --language` |

## Non-negotiables

- `--language` stays byte-identical ASCII in **every** locale (it is a CLI flag, not prose).
- `Minecraft` stays Latin, never transliterated into Cyrillic/Arabic/Thai.
- Keep the single `…` (U+2026), not three ASCII dots.
- Values must end with `,` — a dropped comma on the last inserted line is the #1 cause of
  `TS1005: ',' expected` in these batches.

## Constructed-language names — use the established local form

Do **not** transliterate from the English spelling. What shipped / what to mirror:

| locale | Klingon | Quenya | toki pona |
|---|---|---|---|
| zh-CN | 克林贡语 | 昆雅精灵语 | 道本语 |
| zh-TW | 克林貢語 | 昆雅精靈語 | 道本語 |
| ru | клингонский | квенья | токи-пона |
| uk | клінгонська | **кенська** (not «квенья») | токі-пона |
| sr (Cyrillic) | клингонски | квенјски | токи-пона |
| sk | klingončina | quenya | toki pona |
| sl | klingonščina | quenja | toki pona |
| de | Klingonisch | Quenya | Toki Pona |
| sv | klingoniska | quenya | toki pona |

Thai / Vietnamese / Swahili / Turkish / Albanian UI keeps `Klingon, Quenya, toki pona` in Latin
inside the local sentence — that is idiomatic, not a missed translation.

## Verified values (13-locale batch: 86 keys each, `tsc --noEmit` + `npm run build` green)

```ts
// ru
'instances.languageAuto': 'Язык игры: по настройкам игры',
'instances.language': 'Язык игры',
'instances.languageCommon': 'Часто используемые языки',
'instances.languageMore': 'Ещё языки (вкл. клингонский, квенья, токи-пона…)',
'instances.languageDesc': 'Игровой язык Minecraft — передаётся игре как --language',

// uk
'instances.languageAuto': 'Мова гри: за налаштуваннями гри',
'instances.language': 'Мова гри',
'instances.languageCommon': 'Розповсюджені мови',
'instances.languageMore': 'Інші мови (укл. клінгонська, кенська, токі-пона…)',
'instances.languageDesc': 'Мова в грі Minecraft — передається грі як --language',

// sr (Cyrillic)
'instances.languageAuto': 'Језик игре: прати поставке игре',
'instances.language': 'Језик игре',
'instances.languageCommon': 'Чести језици',
'instances.languageMore': 'Још језика (укл. клингонски, квенјски, токи-пона…)',
'instances.languageDesc': 'Језик унутар Minecraft — преноси се игри као --language',

// sk
'instances.languageAuto': 'Jazyk hry: podľa nastavenia hry',
'instances.language': 'Jazyk hry',
'instances.languageCommon': 'Časté jazyky',
'instances.languageMore': 'Viac jazykov (vrátane klingončiny, quenya a toki pona…)',
'instances.languageDesc': 'Jazyk vo hre Minecraft — prenáša sa hre cez --language',

// sv
'instances.languageAuto': 'Spelspråk: följer spelets inställningar',
'instances.language': 'Spelspråk',
'instances.languageCommon': 'Vanliga språk',
'instances.languageMore': 'Fler språk (inkl. klingoniska, quenya, toki pona…)',
'instances.languageDesc': 'Minecrafts in-game-språk — skickas till spelet som --language',

// sq
'instances.languageAuto': 'Gjuha e lojës: ndjek konfigurimin e lojës',
'instances.language': 'Gjuha e lojës',
'instances.languageCommon': 'Gjuhët e zakonshme',
'instances.languageMore': 'Më shumë gjuhë (përmb. klingon, quenja, toki pona…)',
'instances.languageDesc': 'Gjuha brenda Minecraft — i kalohet lojës si --language',

// sw
'instances.languageAuto': 'Lugha ya mchezo: inafuata mipangilio ya mchezo',
'instances.language': 'Lugha ya mchezo',
'instances.languageCommon': 'Lugha za kawaida',
'instances.languageMore': 'Lugha nyingine (ikiwa Klingon, Quenya, toki pona…)',
'instances.languageDesc': 'Lugha ya Minecraft ndani ya mchezo — inapewa mchezo kama --language',

// tr
'instances.languageAuto': 'Oyun dili: oyun ayarlarına uyar',
'instances.language': 'Oyun dili',
'instances.languageCommon': 'Sık kullanılan diller',
'instances.languageMore': 'Diğer diller (Klingon, Quenya, toki pona dahil…)',
'instances.languageDesc': 'Minecraft oyun içi dili — oyuna --language olarak geçirilir',

// th
'instances.languageAuto': 'ภาษาเกม: ตามการตั้งค่าของเกม',
'instances.language': 'ภาษาเกม',
'instances.languageCommon': 'ภาษาที่ใช้บ่อย',
'instances.languageMore': 'ภาษาเพิ่มเติม (รวม Klingon, Quenya, toki pona…)',
'instances.languageDesc': 'ภาษาในเกม Minecraft — ส่งต่อให้เกมผ่าน --language',

// vi
'instances.languageAuto': 'Ngôn ngữ trò chơi: theo cài đặt trò chơi',
'instances.language': 'Ngôn ngữ trò chơi',
'instances.languageCommon': 'Ngôn ngữ phổ biến',
'instances.languageMore': 'Thêm ngôn ngữ (gồm Klingon, Quenya, toki pona…)',
'instances.languageDesc': 'Ngôn ngữ trong Minecraft — truyền cho trò chơi dưới dạng --language',

// ur (RTL)
'instances.languageAuto': 'کھیل کی زبان: کھیل کی ترتیبات کے مطابق',
'instances.language': 'کھیل کی زبان',
'instances.languageCommon': 'عام زبانیں',
'instances.languageMore': 'مزید زبانیں (بشمول کلنگن، کوینیا، توکی پونا…)',
'instances.languageDesc': 'Minecraft کی اندرونی کھیل زبان — کھیل کو --language کے طور پر دی جاتی ہے',

// zh-TW
'instances.languageAuto': '遊戲語言：跟隨遊戲設置',
'instances.language': '遊戲語言',
'instances.languageCommon': '常用語言',
'instances.languageMore': '更多語言（含克林貢語、昆雅精靈語、道本語…）',
'instances.languageDesc': 'Minecraft 遊戲內語言 —— 以 --language 參數傳給遊戲',
```

## Known defects in the shipped batch — fix if you touch these files

- **sl.ts**: shipped `'Jezek igre…'` / `'Jezek znotraj Minecrafta…'`. Correct Slovenian is
  `Jezik` (`Jezik igre: sledi nastavitvam igre`, `Jezik znotraj Minecrafta — prenese se igri kot
  --language`). `Jezek` is not a word — a generator slip that the count/type checks cannot see.
  Lesson: for Slavic locales, spot-read the inserted `language`-key value in a native form; a
  one-character stem error passes every automated gate.
- **zh-TW.ts**: the spec dictated `跟隨遊戲設置`. Taiwan UI convention is `設定`, and this repo's
  existing zh-TW strings use `設定` elsewhere — if the spec did not fix the wording, prefer
  `跟隨遊戲設定` for consistency inside the same file.
