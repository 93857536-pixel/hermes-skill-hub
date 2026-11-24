# Launcher UI Term Sheet (zh-TW / ja / ko / de / fr / es / it / pt-BR)

Verified wording produced and runtime-checked while localizing CraftCraft Launcher
(`src/i18n/locales/`). Use this to keep follow-up batches (nl, sv, da, nb, ru, pl, uk, tr…)
consistent with what already shipped, and to avoid re-deciding the same vocabulary.

## Base key set — `en.ts` had **81** keys (a brief claiming 87 was wrong)

Group order is meaningful; new locale files must mirror it exactly.

| Group | Keys |
|---|---|
| app | `app.name` |
| nav | `nav.instances`, `nav.newInstance`, `nav.java`, `nav.logs`, `nav.servers`, `nav.settings` |
| common (14) | `common.cancel`, `create`, `save`, `delete`, `del`, `edit`, `launch`, `all`, `filter`, `add`, `test`, `refresh`, `downloading`, `optional` |
| instances (10) | `instances.title`, `count_one`, `count_other`, `filteredBy`, `empty.title`, `empty.desc`, `deleteConfirm`, `launchFailed`, `addTag`, `newCard` |
| wizard (14) | `wizard.title`, `name`, `namePlaceholder`, `version`, `versionPlaceholder`, `notInManifest`, `loader`, `accountName`, `maxMemory`, `javaRuntime`, `jdkAvailable`, `noJdk`, `createFailed`, `create` |
| java (12) | `java.title`, `downloadTemurin`, `installed`, `col.version`, `col.path`, `col.vendor`, `col.arch`, `col.type`, `managed`, `system`, `empty`, `legacyNote` |
| logs (7) | `logs.title`, `noSelection`, `noSelectionDesc`, `createInstance`, `selectInstance`, `autoRefresh`, `empty` |
| servers (9) | `servers.title`, `addServer`, `address`, `name`, `online`, `offline`, `players`, `clickTest`, `empty` |
| settings (7) | `settings.title`, `defaultMaxMemory`, `defaultMinMemory`, `autoSwitchLogs`, `save`, `language`, `languageDesc`, `saved` |

Placeholders in play: `{n}` (counts), `{msg}` (error suffixes), `{tag}`, `{name}`,
`{online}`/`{max}`. `instances.count_one` / `count_other` are the future plural-form hooks.

## Core vocabulary (as shipped)

| en | zh-TW | ja | ko | de | fr | es | it | pt-BR |
|---|---|---|---|---|---|---|---|---|
| Instances | 實例 | インスタンス | 인스턴스 | Instanzen | Instances | Instancias | Istanze | Instâncias |
| New Instance | 新增實例 | 新規インスタンス | 새 인스턴스 | Neue Instanz | Nouvelle instance | Nueva instancia | Nuova istanza | Nova instância |
| Settings | 設定 | 設定 | 설정 | Einstellungen | Paramètres | Ajustes | Impostazioni | Configurações |
| Servers | 伺服器 | サーバー | 서버 | Server | Serveurs | Servidores | Server | Servidores |
| Logs | 日誌 | ログ | 로그 | Logs | Journaux | Registros | Log | Logs |
| Save | 儲存 | 保存 | 저장 | Speichern | Enregistrer | Guardar | Salva | Salvar |
| Create | 建立 | 作成 | 만들기 | Erstellen | Créer | Crear | Crea | Criar |
| Delete | 刪除 | 削除 | 삭제 | Löschen | Supprimer | Eliminar | Elimina | Excluir |
| Del (abbr.) | 刪除 | 削除 | 삭제 | Löschen | Suppr. | Elim. | Elim. | Excl. |
| Launch | 啟動 | 起動 | 실행 | Starten | Lancer | Iniciar | Avvia | Iniciar |
| Refresh | 重新整理 | 更新 | 새로 고침 | Aktualisieren | Actualiser | Actualizar | Aggiorna | Atualizar |
| Loader | 載入器 | ローダー | 로더 | Loader | Chargeur | Cargador | Loader | Carregador |
| Max Memory (MB) | 最大記憶體 | 最大メモリ | 최대 메모리 | Max. Arbeitsspeicher | Mémoire max. | Memoria máx. | Memoria max | Memória máx. |
| Java Runtime | Java 執行環境 | Java ランタイム | Java 런타임 | Java-Laufzeit | Runtime Java | Entorno de ejecución Java | Runtime Java | Runtime do Java |
| Installed JDKs | 已安裝的 JDK | インストール済みの JDK | 설치된 JDK | Installierte JDKs | JDK installés | JDK instalados | JDK installati | JDKs instalados |
| Vendor | 廠商 | ベンダー | 공급업체 | Anbieter | Fournisseur | Proveedor | Fornitore | Fornecedor |
| Arch | 架構 | アーキテクチャ | 아키텍처 | Architektur | Arch. | Arquitectura | Architettura | Arquitetura |
| Managed | 受管理 | 管理対象 | 관리됨 | Verwaltet | Géré | Gestionado | Gestito | Gerenciado |
| address:port | 位址:連接埠 | アドレス:ポート | 주소:포트 | adresse:port | adresse:port | dirección:puerto | indirizzo:porta | endereço:porta |
| Online / Offline | 線上 / 離線 | オンライン / オフライン | 온라인 / 오프라인 | Online / Offline | En ligne / Hors ligne | En línea / Sin conexión | Online / Offline | Online / Offline |

## Decisions worth not re-litigating

- **de `Logs` not `Protokolle`** — idiomatic in German dev tooling, and the nav slot is narrow.
  `Protokolle` is correct German but overflows the tab.
- **zh-TW vocabulary, not character conversion**: 設定 / 儲存 / 建立 / 伺服器 / 記憶體 / 執行環境 /
  連結埠. Simplified `设置/保存/创建` mechanically converted would read mainland-flavored.
- **pt-BR over pt-PT**: Configurações / Excluir / Salvar / Runtime do Java. `Ajustes`+`Eliminar`
  is the European reading and is what es/pt would collide with.
- **es keeps `Ajustes`** (not `Configuración`/`Configuraciones`) — the standard macOS Spanish
  menu term; already used consistently across the app shell.
- **it/ja/ko keep `Loader`/`ローダー`/`로더`** — the Minecraft community borrowed form, not a
  literal translation.
- **`common.del` is a button abbreviation** everywhere: two-to-six glyphs, never a full verb.
- **Quoted UI label inside a string uses native quotes**, which also dodges escaping:
  `« Tester »` (fr/es), `„Testen“` (de), `「テスト」`/`「테스트」` (ja/ko).
- **fr/it apostrophes**: prefer phrasing that avoids them (`Aucune instance pour le moment`,
  `usato così com\'è`), else escape as `\'`. A missed one is the single most likely
  `tsc --strict` failure in a batch like this.
- **Brands verbatim**: CraftCraft, Java, JDK, Temurin, Minecraft, Rosetta 2, MB, x86_64.
  `java.legacyNote` is the key that carries most of them — check it explicitly.

## Regenerating a follow-up batch

1. `node <skill>/scripts/verify-locales.mjs` against the existing 9 files first — confirm the
   baseline still passes before adding new ones.
2. Write the new locales against the 81-key contract above (still: count from `en.ts`, the
   contract can move).
3. Re-run with `--runtime`, then `npm run build`, then grep the bundle for a distinctive
   translation. If nothing imports the i18n entry, the strings are not shipped — say so.
