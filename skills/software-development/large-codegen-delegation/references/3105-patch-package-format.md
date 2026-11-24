# 3105 补丁包格式事实 + DTBP envelope 设计(2026-09-05 还原)

把 GPL 项目 3105(GitHub YangJiiii/3105)的补丁包编解码**干净移植**时还原的格式事实。铁律:仅还原
**格式/加密参数**(互操作所需,不受版权保护),代码表达原创、禁止逐行复制。实测产物:`Sources/PatchWorkspace/PackageCodec.swift`
(自有 DTBP 格式 + `import3105Package` 兼容导入),22 条单测全绿。

## 3105 格式事实(v1-v3,还原自 PatchPackageCodec.swift / PatchProjectModels.swift)

- **magic**: `3105PATCH\0`(10 字节),后面紧跟 envelope 的**二进制 plist**(`PropertyListEncoder().outputFormat = .binary`)。
- **envelope 字段**(CodingKeys 即属性名,须逐字对齐):`schemaVersion:Int`、`keyAADVersion:Int?`、`packageID:UUID`、
  `isPasswordProtected:Bool`、`kdfSalt:Data?`(16B)、`kdfIterations:Int?`、`wrappedContentKey:Data?`、
  `publicContentKey:Data?`、`keyFingerprint:Data`(32B = SHA256(contentKey))、`encryptedPayload:Data`。
  nil 的 optional 在 plist 里**省略键**(合成 Codable 的 `encodeIfPresent` 行为),解码侧缺键即 nil。
- **payload**: 也是二进制 plist,`{project: PatchProject, replacementDigests: [ruleID.uuidString: Data(SHA256(replacementData))]}`。
- **加密**: contentKey = 32 随机字节。AES-GCM(CryptoKit)combined 输出(nonce12+ciphertext+tag16)。密码路径:
  PBKDF2-HMAC-SHA256(`CCKeyDerivationPBKDF`, salt 16B, iterations 100k~1M, 默认 250k, 输出 32B)派生 wrappingKey,
  再 AES-GCM 包裹 contentKey → `wrappedContentKey`。无密码路径 `publicContentKey = contentKey`。
- **AAD 字符串**:key 包裹/解包用 `3105PATCH/v<ver>/key/<packageID.uuidString>`,payload 用 `3105PATCH/v<ver>/payload/<packageID.uuidString>`。
  **解包时版本用 `envelope.keyAADVersion ?? envelope.schemaVersion`**,payload 恒用 `envelope.schemaVersion`。
- **schema 1-3 差异**: v1/v2 私密包不支持(`isPrivate` 需 v3 + 有密码);`keyAADVersion` 仅在受密码保护时置为 schemaVersion,
  否则 nil。解码需 `(1...3).contains(schemaVersion)` 否则抛 `unsupportedVersion`。
- **bundleID 语义映射**(关键):3105 的 `rule.bundleID + rule.relativePath` → 我们模型的单一 `relativePath = "<bundleID>/<relativePath>"`;
  `directories[]` → `addFolder` 规则;`rules[]` → `replaceFile` 规则(replacementFilename 空串 → nil);`origin` 记录 repositoryName/URL/packageIdentifier。

## 自有 DTBP 格式(自设计,参照同 envelope 思路)

- magic `DTBP1PACK\0` + **JSON** envelope(同 3105 字段集,schemaVersion=1);payload 为 JSON `{project, replacementDigests}`。
  JSON 编码 Data 自动 base64、UUID 自动 string;日期用默认 deferredToDate(Double,**无损**,别用 `.iso8601`——会丢亚秒精度导致 round-trip 不等)。
- AAD 前缀换 `DTBP/v<ver>/key|payload/<id>`。PBKDF2 参数同 3105。
- 公开 API:`encodePackage(project, password?) -> Data`、`decodePackage(Data, password?) -> DecodedPackage{project,contentKey,format}`、
  `import3105Package(Data, password?, origin?) -> PatchProject`、`detectFormat(Data)`(按 magic 前缀分流)。

## 无真实 .3105 fixture 时的确定性验证法

/tmp/3105 无真实 `.3105` 字节流。按 SPEC 允许的「自产 v3 结构构造」:在**测试文件里独立写一个 fixture builder**
(自己声明镜像字段的 Codable 结构 + 直接用 CryptoKit/CommonCrypto 组包,不复用产品代码),分别构造 v1/v2 无密码与 v3 带密码包,
再喂 `import3105Package` 断言 bundleID 前缀映射 / `directories→addFolder` / `rules→replaceFile` / origin 记录。这验证的是
「我的解码正确逆转了文档化格式」;真实包的残余风险只在未察觉的序列化细节(如 UUID 在 plist 里的编码),集成期可用真实包补一次端到端。

## 实现注意(Swift 6)

- 传 `(Int) -> Data` 闭包时若闭包体不用参数,Swift 6 报 `contextual type for closure argument list expects 1 argument, which cannot be implicitly ignored`。
  用 `$0` 或 `{ _ in ... }`;常见错误是 `keyAAD: { aad(version: someExpr) }`(忘了参数自己重算)——语义等价但编译失败,改 `$0` 即绿。
- 事务(apply/restore)journal 用二进制 plist(`journal.plist`),记录 `originalExisted/backupFilename/originalDigest/replacementDigest`,
  restore 逆序 `Data.write(to:.atomic)` 做字节级还原;`resolveTargetURL` 要**逐组件 appendPathComponent**(别把含 `/` 的整串当单组件),再 `standardizedFileURL` + 前缀守卫防穿越。
