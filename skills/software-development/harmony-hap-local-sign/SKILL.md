---
name: harmony-hap-local-sign
description: "Use when 给鸿蒙 .hap 本地 pki_internal 签名(无 AGC profile)。"
version: 1.0.0
---

# HarmonyOS .hap 本地 pki_internal 签名

触发条件: 本机有 HarmonyOS Command Line Tools(~/command-line-tools)但没有华为 AGC 的 .p7b/.cer 签名 profile,需要给 .hap 做出可分发的签名单(不绑设备 UDID,任意鸿蒙设备可装)。

已实战配方(2026-10 某聊天App): 可复用脚本见
`~/Programming/Projects/某聊天App/harmony/sign-local.sh`(改 HAP_IN/BUNDLE_NAME 即可复用)。

## 关键配方

1. **JDK**: 需要 JDK 17。本机 `brew openjdk@17` 已装但 `/usr/libexec/java_home` 找不到(未链到系统目录),直接用
   `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`。

2. **证书材料** 全在 `~/command-line-tools/sdk/default/26.0.0/toolchains/lib/`:
   - `OpenHarmony.p12`(口令 123456, 含 root CA / Application CA(子CA) / application release 密钥)
   - `OpenHarmonyProfileRelease.pem`(根→子CA→Profile 证书链, sign-profile 的 `-profileCertFile` 直接用它)

3. **坑 1 — 链顺序**: 证书链必须 **根→子CA→叶**。SDK 自带 .pem 是正确顺序;自己 keytool 导出后手动 cat 成 叶→根 会报 `Signature does not match`。

4. **坑 2 — 占位自签证书**: p12 里 `openharmony application release` 的证书是**自签占位**(subject==issuer),直接当 appCertFile 拼链必失败。解法: 用 openssl 让**子 CA** 给 app 私钥重签一张真证书:
   ```bash
   # 导出 p12 全部 cert/key(按 subject 定位角色, 按公钥 hash 匹配 cert<->key)
   openssl pkcs12 -in $P12 -nokeys -nodes -passin pass:123456 -out all-certs.pem
   openssl pkcs12 -in $P12 -nocerts -nodes -passin pass:123456 -out all-keys.pem
   # 子CA 签 app 证书(10 年, 带 basicConstraints CA:FALSE + digitalSignature)
   openssl req -new -key $APP_KEY -subj "/C=CN/O=OpenHarmony/OU=OpenHarmony Team/CN=OpenHarmony Application Release" -out app.csr
   openssl x509 -req -in app.csr -CA $SUBCA -CAkey $SUBCA_KEY -CAcreateserial \
     -out app.cer -days 3650 -sha256 -extfile appext.cnf
   # 组链: 根 + 子CA + app.cer (cat 顺序即链顺序)
   ```
   appext.cnf: `basicConstraints=critical,CA:FALSE` + `keyUsage=critical,digitalSignature`

5. **坑 3 — generate-app-cert 的隐藏必填参数**: 该子命令 help 没列全, 实际还要 `-subCaCertFile <子CA证书pem>`, 缺了报 `Param {subCaCertFile} is required`。

6. **签名调用**(keyAlias/口令都来自 p12):
   ```bash
   java -jar $LIB/hap-sign-tool.jar sign-profile -mode localSign \
     -keyAlias "openharmony application profile release" -keyPwd 123456 \
     -profileCertFile "$LIB/OpenHarmonyProfileRelease.pem" \
     -inFile profile.json -signAlg SHA256withECDSA \
     -keystoreFile "$LIB/OpenHarmony.p12" -keystorePwd 123456 \
     -outFile signed-profile.p7b
   java -jar $LIB/hap-sign-tool.jar sign-app -mode localSign \
     -keyAlias "openharmony application release" -keyPwd 123456 \
     -appCertFile app-chain.cer -profileFile signed-profile.p7b \
     -inFile 未签名.hap -signAlg SHA256withECDSA \
     -keystoreFile "$LIB/OpenHarmony.p12" -keystorePwd 123456 \
     -outFile 签名.hap -compatibleVersion 12 -signCode 1 -permSign 1
   ```
   profile.json 的 `bundle-info.distribution-certificate` 要填 app 证书 PEM(空字符串会报 `Common name of certificate is empty`);
   `type: release` + 无 `debug-info.device-ids` = 不绑设备。

7. **验证**:
   ```bash
   java -jar $LIB/hap-sign-tool.jar verify-app -inFile 签名.hap -outCertChain c.cer -outProfile p.p7b
   java -jar $LIB/hap-sign-tool.jar verify-profile -inFile p.p7b -outFile r.json
   # r.json: {verifiedPassed:true, content:{type, validity, ...}} (profile 在 .content 下, 不是顶层)
   ```
   签名成功的 hap 比未签名多 `.pages.info` 条目, 体积 +~35KB。

## 验证 ad-hoc 方法(无测试套件时)
临时脚本: ① bash -n 检查脚本语法 ② 产物 size 对比 ③ 独立 verify-app 复核(不信任构建脚本自报) ④ unzip -l 条目数 ⑤ verify-profile 导出 JSON 断言 type=release 且无 device-ids。

## 分发
签名 hap 放桌面并同步 GitHub Release; 安装: 鸿蒙手机直接打开 hap 或 `hdc install xxx.hap`。纯 Web 壳应用需联网。
