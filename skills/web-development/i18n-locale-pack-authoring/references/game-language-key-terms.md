# `instances.language*` — shipped wording across 32 locales (two batches)

Verified strings for the five "game language" keys (CraftCraft Launcher, `src/i18n/locales/`).
English reference values:

| key | en |
|---|---|
| `instances.languageAuto` | Game language: follow game |
| `instances.language` | Game language |
| `instances.languageCommon` | Common languages |
| `instances.languageMore` | More languages (incl. Klingon, Quenya, toki pona…) |
| `instances.languageDesc` | Minecraft in-game language — passed to the game as `--language` |

Rules applied: `--language` stays byte-identical (it is a CLI flag, not prose); `Minecraft`
stays Latin in every language; Klingon/Quenya/toki pona are localised only where a native form
is established (ja/ko), otherwise kept as Latin proper nouns.

## Shipped values

| loc | languageAuto | language | languageCommon | languageMore | languageDesc |
|---|---|---|---|---|---|
| he | שפת המשחק: עוקבת את הגדרות המשחק | שפת המשחק | שפות נפוצות | שפות נוספות (כולל Klingon, Quenya, toki pona…) | שפת המשחק של Minecraft — מועברת למשחק באמצעות --language |
| hi | खेल की भाषा: खेल की सेटिंग्स के अनुसार | खेल की भाषा | सामान्य भाषाएँ | अधिक भाषाएँ (Klingon, Quenya, toki pona सहित…) | Minecraft की इन-गेम भाषा — खेल को --language पैरामीटर के रूप में भेजी जाती है |
| hr | Jezik igre: prati postavke igre | Jezik igre | Česti jezici | Više jezika (uključujući Klingon, Quenya, toki pona…) | Jezik unutar Minecrafta — proslijeđuje se igri kao --language |
| hu | Játéknyelv: követi a játék beállításait | Játéknyelv | Gyakorlatos nyelvek | További nyelvek (Klingon, Quenya, toki pona…) | A Minecraft játékban használt nyelv — a játéknak --language paraméterként átadva |
| id | Bahasa permainan: mengikuti pengaturan permainan | Bahasa permainan | Bahasa umum | Bahasa lain (termasuk Klingon, Quenya, toki pona…) | Bahasa dalam permainan Minecraft — diteruskan ke permainan sebagai --language |
| is | Leikmál: fylgir stillingum leiks | Leikmál | Algeng tungumál | Fleiri tungumál (milli annars Klingon, Quenya, toki pona…) | Tungumál innan í Minecraft — gefið leiknum sem --language |
| it | Lingua del gioco: segue le impostazioni del gioco | Lingua del gioco | Lingue comuni | Altre lingue (incl. Klingon, Quenya, toki pona…) | Lingua in-game di Minecraft — passata al gioco come --language |
| ja | ゲーム言語：ゲーム設定に従う | ゲーム言語 | よく使う言語 | その他の言語（クリンゴン語・クウェンヤ語・トーキポナを含む…） | Minecraft のゲーム内言語 — --language 引数としてゲームに渡します |
| ko | 게임 언어: 게임 설정을 따름 | 게임 언어 | 자주 쓰는 언어 | 추가 언어 (클링온어, 퀘뉴아어, 토키포나 포함…) | Minecraft 게임 내 언어 — --language 인자로 게임에 전달됩니다 |
| lt | Žaidimo kalba: seka žaidimo nustatymus | Žaidimo kalba | Populiarios kalbos | Daugiau kalbų (įskaitant Klingon, Quenya, toki pona…) | Minecraft kalba žaismui — perduodama žaidimui kaip --language |
| lv | Spēles valoda: seko spēles iestatījumiem | Spēles valoda | Biežāk lietotās valodas | Vairāk valodu (t.sk. Klingon, Quenya, toki pona…) | Minecraft valoda spēlē — nodota spēlei kā --language |
| mk | Јазик на играта: следи ги поставките на играта | Јазик на играта | Чести јазоци | Повеќе јазоци (вклучувајќи Klingon, Quenya, toki pona…) | Јазик во Minecraft — се пренесува во играта како --language |
| ms | Bahasa permainan: ikut tetapan permainan | Bahasa permainan | Bahasa biasa | Lagi bahasa (termasuk Klingon, Quenya, toki pona…) | Bahasa dalam permainan Minecraft — dihantar ke permainan sebagai --language |
| nb | Spilkspråk: følger spillinnstillingene | Spilkspråk | Vanlige språk | Flere språk (inkl. Klingon, Quenya, toki pona…) | Spilkspråk i Minecraft — gitt til spillet som --language |
| nl | Speltaal: volgt de spelinstellingen | Speltaal | Gangbare talen | Meer talen (o.a. Klingon, Quenya, toki pona…) | Speltaal in Minecraft — doorgegeven aan het spel als --language |
| pl | Język gry: zgodnie z ustawieniami gry | Język gry | Popularne języki | Więcej języków (m.in. Klingon, Quenya, toki pona…) | Język w grze Minecraft — przekazywany do gry jako --language |

## Second batch — af/ar/bg/ca/cs/cy/da/de/el/eo/es/et/fa/fi/fil/fr

Shipped and verified (same five keys, same English reference values above).

| loc | languageAuto | language | languageCommon | languageMore | languageDesc |
|---|---|---|---|---|---|
| af | Speltaal: volg die speletjie se instellings | Speltaal | Algemene tale | Meer tale (insluitend Klingon, Quenya en toki pona…) | Minecraft-speletjietaal — aan die speletjie deurgegee as --language |
| ar | لغة اللعبة: تتبع إعدادات اللعبة | لغة اللعبة | اللغات الشائعة | المزيد من اللغات (تشمل الكلينغونية والكوينيا وتوكي بونا…) | لغة لعبة ماينكرافت داخل اللعبة — تُمرَّر إلى اللعبة عبر معامل --language |
| bg | Език на играта: следва настройките на играта | Език на играта | Често използвани езици | Повече езици (вкл. клингонски, квеня и toki pona…) | Език в играта Minecraft — подава се на играта като параметър --language |
| ca | Idioma del joc: segueix la configuració del joc | Idioma del joc | Idiomes comuns | Més idiomes (incl. klingon, quenya i toki pona…) | Idioma del Minecraft dins del joc — es passa al joc com a --language |
| cs | Jazyk hry: sleduje nastavení hry | Jazyk hry | Obvykle používané jazyky | Další jazyky (včetně klingonštiny, quenye a toki pony…) | Jazyk hry Minecraft — předává se hře jako parametr --language |
| cy | Iaith y gêm: dilyn gosodiadau\'r gêm | Iaith y gêm | Ieithoedd cyffredin | Mwy o ieithoedd (yn cynnwys Klingon, Quenya a toki pona…) | Iaith y gêm Minecraft — a drosglwyddir i\'r gêm fel --language |
| da | Spilsprog: følger spillets indstillinger | Spilsprog | Almindelige sprog | Flere sprog (inkl. klingon, Quenya og toki pona…) | Minecrafts sprog i spillet — sendes til spillet som --language |
| de | Spielsprache: folgt den Spieleinstellungen | Spielsprache | Gebräuchliche Sprachen | Weitere Sprachen (u. a. Klingonisch, Quenya und toki pona…) | Minecraft-Spielsprache – wird dem Spiel als --language übergeben |
| el | Γλώσσα παιχνιδιού: ακολουθεί τις ρυθμίσεις του παιχνιδιού | Γλώσσα παιχνιδιού | Κοινές γλώσσες | Περισσότερες γλώσσες (συμπεριλ. κλίνγκον, κυένα και toki pona…) | Γλώσσα εντός του παιχνιδιού Minecraft — περνάται στο παιχνίδι ως --language |
| eo | Lingvo de la ludo: sekvas la agordojn de la ludo | Lingvo de la ludo | Komunaj lingvoj | Pliaj lingvoj (inkl. klingonon, Quenyan kaj toki ponon…) | Ludlingvo de Minecraft — alportita al la ludo kiel --language |
| es | Idioma del juego: sigue la configuración del juego | Idioma del juego | Idiomas comunes | Más idiomas (incl. klingon, quenya y toki pona…) | Idioma en el juego de Minecraft — se pasa al juego como --language |
| et | Mängukeel: järgib mängu seadeid | Mängukeel | Tüüpilised keeled | Rohkem keeli (sh. klingoni, quenya ja toki pona…) | Minecrafti mängusisene keel — edastatakse mängule parameetrina --language |
| fa | زبان بازی: مطابق تنظیمات بازی | زبان بازی | زبان‌های رایج | زبان‌های بیشتر (شامل کلینگون، کویِنیا و توکی‌پونا…) | زبان داخل بازی ماین‌کرفت — به‌صورت پارامتر --language به بازی منتقل می‌شود |
| fi | Pelikieli: seuraa pelin asetuksia | Pelikieli | Yleiset kielet | Lisää kieliä (mm. Klingon, Quenya ja toki pona…) | Minecraftin pelikieli — välitetään pelille parametrina --language |
| fil | Wika ng laro: sumusunod sa mga setting ng laro | Wika ng laro | Mga karaniwang wika | Higit pang wika (kasama ang Klingon, Quenya at toki pona…) | Wika sa loob ng Minecraft — ipinapasa sa laro bilang --language |
| fr | Langue du jeu : suit les réglages du jeu | Langue du jeu | Langues courantes | Plus de langues (dont Klingon, Quenya et toki pona…) | Langue de Minecraft en jeu – transmise au jeu en tant que --language |

Notes specific to this batch:

- **`cy` is the only file in the set needing escapes**: `gosodiadau\'r`, `i\'r`. Unescaped, the
  apostrophe terminates the TS string and `tsc` reports `TS1002: Unterminated string literal`.
- **Danish `Spilsprog` is one word** — `Spil sprog` is a visible typo. German is
  `Spielsprache` (`Spieldate` is not a word). Filipino is `Wika ng laro` (`Wikaan` is not a
  word). Welsh common-languages is `Ieithoedd cyffredin` (`Ieithydd` = linguist).
- **French uses `Langue`, not `Langage`** — matches the file's own `settings.language`.
  Also note the French spaced colon (` : `) and French spacing before `?`/`!` in this file.
- Afrikaans uses **speletjie** for the game-as-software (`speletjietaal`); `spel` alone reads as
  a played match. Afrikaans common-languages is `Algemene tale`, not `Gewone`.
- Conlang names: localised where a settled form exists — bg `клингонски/квеня`, el
  `κλίνγκον/κυένα`, cs `klingonština/quenya`, et `klingoni`, ar `الكلينغونية/الكوينيا`, fa
  `کلینگون/کویِنیا`. Latin proper nouns kept in af/ca/cy/da/de/eo/es/fi/fil/fr.
- Dashes: `de` and `fr` use the en dash `–`; the rest use the em dash `—` (ar included, for
  consistency with the other 15 — a plain hyphen looks like a minus next to `--language`).
- fa keeps ZWNJ in `زبان‌های`; do not replace with a plain space.

## Notes for extending this set

- Hungarian uses **Játéknyelv** (Mojang's Hungarian pack says `Jelnyelv`, which is also
  defensible) — keep one form across the whole language, don't mix.
- Norwegian `Spilkspråk` is one word; `Spill språk` is wrong.
- Icelandic has no native verb for "follow settings"; `fylgir stillingum leiks` is the idiomatic
  choice.
- Latvian/Lithuanian keep `Klingon/Quenya/toki pona` in Latin — no established native forms.
- Japanese/Korean are the only two of this set with settled native spellings
  (クリンゴン語/クウェンヤ語/トーキポナ, 클링온어/퀘뉴아어/토키포나).
- Baseline count in this repo before the insertion: 81 quoted keys per file → 86 after these 5.
  `grep -cE "^\s*'" <file>.ts` is the check.
