# Version-selector block — `wizard.*` + `instances.versionDesc` (7 keys)

Shipped in CraftCraft v0.3.x. Base English (from `en.ts`), meaning each key must carry:

| key | en |
|---|---|
| `wizard.selectVersion` | Please select a version… |
| `wizard.releases` | Releases |
| `wizard.snapshots` | Snapshots |
| `wizard.oldBeta` | Old Beta |
| `wizard.oldAlpha` | Old Alpha |
| `wizard.showSnapshots` | Include snapshots ({n}) |
| `instances.versionDesc` | Switch game version (applies on next launch) |

## Verified values — 15 locales (batch 2026-11, all 93-key clean, tsc + build green)

| locale | selectVersion | releases | snapshots | oldBeta | oldAlpha | showSnapshots | versionDesc |
|---|---|---|---|---|---|---|---|
| pt-BR | `Selecione uma versão…` | `Lançamentos` | `Snapshots` | `Beta antigo` | `Alpha antigo` | `Incluir snapshots ({n})` | `Alterar a versão do jogo (aplica-se na próxima inicialização)` |
| ro | `Selectați o versiune…` | `Versiuni finale` | `Snapshot-uri` | `Beta vechi` | `Alpha vechi` | `Include snapshot-uri ({n})` | `Schimbă versiunea jocului (se aplică la următoarea pornire)` |
| ru | `Выберите версию…` | `Релизы` | `Снимки` | `Старая бета` | `Старая альфа` | `Включая снимки ({n})` | `Сменить версию игры (применится при следующем запуске)` |
| sk | `Vyberte verziu…` | `Vydania` | `Snímky` | `Staršia beta` | `Staršia alfa` | `Zahrnúť snímky ({n})` | `Zmeniť verziu hry (prejaví sa pri ďalšom spustení)` |
| sl | `Izberite različico…` | `Izdaje` | `Posnetki` | `Starejša beta` | `Starejša alfa` | `Vključi posnetke ({n})` | `Spremeni različico igre (uveljavi se ob naslednjem zagonu)` |
| sq | `Zgjidh një version…` | `Versionet zyrtare` | `Versionet e ndërmjetme` | `Beta e vjetër` | `Alfa e vjetër` | `Përfshi versionet e ndërmjetme ({n})` | `Ndrysho versionin e lojës (zbatohet në nisjen tjetër)` |
| sr | `Изаберите верзију…` | `Издања` | `Снимци` | `Стара бета` | `Стара алфа` | `Укључи снимке ({n})` | `Промени верзију игре (примењује се при следећем покретању)` |
| sv | `Välj en version…` | `Utgåvor` | `Ögonblicksbilder` | `Gammal beta` | `Gammal alfa` | `Inkludera ögonblicksbilder ({n})` | `Byt spelversion (gäller vid nästa start)` |
| sw | `Chagua toleo…` | `Matoleo rasmi` | `Matoleo ya snapshot` | `Beta ya zamani` | `Alpha ya zamani` | `Jumuisha matoleo ya snapshot ({n})` | `Badilisha toleo la mchezo (hutumika kwenye uzinduzi unaofuata)` |
| th | `เลือกเวอร์ชัน…` | `เวอร์ชันทางการ` | `สแนปช็อต` | `เบต้าเก่า` | `อัลฟาเก่า` | `รวมสแนปช็อต ({n})` | `สลับเวอร์ชันเกม (มีผลเมื่อเริ่มเกมครั้งถัดไป)` |
| tr | `Bir sürüm seçin…` | `Yayın sürümleri` | `Anlık görüntüler` | `Eski beta` | `Eski alfa` | `Anlık görüntüleri dahil et ({n})` | `Oyun sürümünü değiştir (sonraki başlatmada geçerli olur)` |
| uk | `Виберіть версію…` | `Релізи` | `Знімки` | `Стара бета` | `Стара альфа` | `Включно зі знімками ({n})` | `Змінити версію гри (застосується під час наступного запуску)` |
| ur | `ایک ورژن منتخب کریں…` | `ریلیز` | `اسنیپ شاٹس` | `پرانا بیٹا` | `پرانا الفا` | `اسنیپ شاٹس شامل کریں ({n})` | `گیم ورژن تبدیل کریں (اگلی بار لانچ پر لاگو ہوگا)` |
| vi | `Chọn phiên bản…` | `Bản phát hành` | `Bản snapshot` | `Beta cũ` | `Alpha cũ` | `Bao gồm bản snapshot ({n})` | `Đổi phiên bản trò chơi (áp dụng ở lần khởi động sau)` |
| zh-TW | `選擇版本…` | `正式版` | `快照版` | `遠古 Beta` | `遠古 Alpha` | `包含快照版（{n}）` | `切換遊戲版本（下次啟動生效）` |

## Terminology notes to reuse when extending to the remaining locales

- **Snapshot follows the official Minecraft locale where one exists**, not a dictionary gloss:
  ru `Снимки`, sr `Снимци`, sk `Snímky`, sl `Posnetki`, uk `Знімки`, tr `Anlık görüntüler`,
  sv `Ögonblicksbilder`, th `สแนปช็อต`, pt-BR/vi/es-style `Snapshot`/`Bản snapshot`.
  Languages with no MC precedent (sq, sw) get either a native compound
  (sq `Versionet e ndërmjetme`) or the borrowed noun (sw `Matoleo ya snapshot`) — pick one and
  keep it consistent inside that language.
- **"Old Beta / Old Alpha" is `old` as in ancient, not `previous`**: ru `Старая`, uk `Стара`,
  sr `Стара`, sk/sl `Staršia` (comparative) — `遠古` in zh-TW. Do not render as `предыдущая`.
- **`versionDesc` is a sentence, `selectVersion` is a label**: the desc keeps the parenthetical
  "applies on next launch" clause in every locale; do not drop it to save width.
- **zh-TW wraps the count in full-width parens `（{n}）`** — correct, and it defeats a
  `grep "({n})"` check (see the placeholder pitfall in SKILL.md). Same convention is fine for
  `zh-CN` and `ja`.

## Batch mechanics that worked

- Anchor: `old_string = "};\n\nexport default <identifier>;"` (identifiers: `ptBR`, `zhTW`,
  others = the ISO code). Assert `grep -c '^};$' f.ts == 1` first.
- 86 → 93 keys per file, `grep -cE "^ *'"` == 93 for all 15.
- Verification: `npx tsc --noEmit` → exit 0, then `npm run build` (`tsc && vite build`) → exit 0.
  Ignore the `patch` lint chatter about `@types/babel__*` / `@types/react` `Set`/`Map`/`Iterable`
  — that comes from the bare-tsc lint runner, not from the locale files.
