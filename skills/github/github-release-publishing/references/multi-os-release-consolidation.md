# 把多系统安装包合并进一个 Release + 清理早期发行版(2026-11 某聊天App v1.0 实测)

用户要"三端包放一个 Release、版本统一、早期全删"时,顺序与坑:

1. **先确认各端真正的"最新"再动手**:`gh release list` + 最新 tag `gh release view <tag> --json assets,body` + 本地 `find . \( -name '*.ipa' -o -name '*.apk' -o -name '*.hap' \)` 三方对账。⚠️ 别信"最新是 vNN"的记忆——**iOS 发行序列号 ≠ 内部版本**:`某聊天App-unsigned-v35.ipa` 是第 35 次出包,但 App 内部是 `CFBundleShortVersionString=1.9 / CFBundleVersion=31`(在 Info.plist / project.yml 读)。资产名带的是序列号,不是内部版本。
2. **删除/重发前,把要上传的本地文件 SHA256 对旧 Release 资产 digest 验一遍**:`shasum -a 256 <本地>` vs `gh release view <old-tag> --json assets --jq '.[].digest'`,逐字一致才直接复用文件上传(本次三端全对上,免重构建)。
3. ⚠️ **`gh release create <tag> --target <sha>` → 422 `Release.target_commitish is invalid`**(当 tag 已存在且指向该 commit 时,本次正是移动旧 tag 后重发踩中)。**修法:去掉 `--target`**,让 gh 用 tag ref 本身:`gh release create v1.0 --title "..." --latest --notes-file body.md`(tag 已 `git push` 过)。多端长说明走 `--notes-file` 模板(见 `templates/release-notes-multiplatform.md`)。
4. ⚠️ **大资产(10MB 级)走 TUN/代理时前台超时**:`gh release upload` 前台在 180s/300s 断。**改 `background=true` + `notify_on_complete` + 重试循环**:
   ```bash
   for i in 1 2 3 4 5; do gh release upload v1.0 <file> --clobber && echo DONE && break; echo "retry $i"; sleep 15; done
   ```
   期间可并行干别的(删旧 Release、扩 README),别干等。
5. ⚠️ **手搓 curl POST 资产 API 会 404,但 gh 能成**:`curl -X POST /releases/{id}/assets?name=x` 与 `POST /releases/tags/{tag}/assets?name=x` 都 `404 Not Found`(代理/multipart 干扰),同一上传 `gh release upload` 却成功。**上传一律用 `gh release upload` / `gh release create <tag> <files...>`,别手搓 asset 上传 URL**(与 SKILL.md「传资产用 gh release upload,别手搓 assets API」条一致,再次实测印证)。
6. ⚠️ **"用真上传命令做 dry-run"不是 dry-run**:为探端点我上传了个 1 字节 `test-probe.txt`,结果真挂上了 live Release → 立即 `gh release delete-asset v1.0 test-probe.txt --yes` 清掉。探端点只用 `gh release view --json assets` / 只读 API,**别 PUT 探针文件**。
7. **批量删旧 Release + 旧 tag(代理抖要带重试)**:逐个 `gh release delete <tag> --yes`(带 `for` 重试)+ 逐个 `git push origin --delete <tag>`;最后 `gh release list`(应只剩新 tag)+ `git ls-remote --tags origin` 验证。
   - 新 tag 要复用同名(如把 9 月旧 `v1.0` 移到新 commit):先 `gh release delete v1.0 --yes` + `git push origin --delete v1.0` + `git tag -d v1.0`,再 `git tag v1.0 <新HEAD>` + `git push origin v1.0`,然后建 Release。
   - 后续 main 有新提交(如 README 扩充)后,把 tag 强移:`git tag -f v1.0 <新commit>` + `git push origin v1.0 -f`。

## TUN 假 IP 诊断细化(补充 SKILL.md「代理诊断」条)

`scutil --proxy` 的 ExceptionsList 含 `198.18.0.0/15` = **TUN 模式**。TUN 下 DNS **永远**返 198.18.x 假 IP(`dig +short github.com` 必见),所以"看见假 IP"≠代理死。真正的连通判据是:
- `nc -z 127.0.0.1 1082`(代理是否在听)
- `curl -o /dev/null -w '%{http_code}' https://api.github.com`(系统代理已自动启用,200 即通)

**假 IP 且 1082 关 = 代理进程死(gh/git 全挂);假 IP 且 1082 开 = 可用只是慢**(本次 10MB APK 上传慢即此态,后台重试 ~12 分钟落地)。

## 验证收尾(本次全 PASS 的判据)

- `gh release list` 应只剩新 tag(1 条,标 Latest)。
- `gh release view v1.0 --json assets` 逐资产:本地 `shasum -a 256` 与远端 `digest`(sha256:...)逐字一致 + `size` 一致。
- `git ls-remote --tags origin` 只剩 `refs/tags/v1.0`(指向最新 main commit)。
- 网络抖时 `gh release view` 会间歇返空/超时 → 用 `curl -H "Authorization: Bearer $(gh auth token)" https://api.github.com/repos/<o>/<r>/releases/tags/<tag>` 直接查 asset digest,带 for 重试。
