---
name: github-mirror-survey
category: devops
description: "GitHub 镜像/代理/加速方案：免费站现状、自建中转、机场订阅选型。"
trigger: "GitHub 访问慢/连不上；需要镜像/代理/机场订阅"
---

# GitHub Mirror / Acceleration Survey

当用户抱怨 GitHub/Release/Clone 慢或连不上时加载此 skill。

## 一、免费镜像站现状（2026-10 起）

> **实测结论：大部分免费镜像已集体失效。** 见下文 references/status-20261030.md。

常见代理形态：

| 形态 | 示例 | 状态 |
|------|------|------|
| gh-proxy 系 | mirror.ghproxy.com / ghproxy.net / ghproxy.link | 多数已挂 |
| 临时镜像 | ghfast.top / ghp.quickso.cn / xiake.pro | 不稳定 |
| 代码托管镜像 | hub.fastgit.xyz / gitclone.com | 间歇可用 |
| NPM 专用 | registry.npmmirror.com / pnpm.taobao.org | 稳定 |

## 二、自建中转方案（推荐）

**在 ECS 上部署 gh-proxy：**

```bash
# 在已有 ECS（如阿里云 cn-beijing）上
cd ~/ && curl -sL https://github.com/hunshcn/gh-proxy/releases/download/v2.1.0/gh-proxy-linux-amd64 -o gh-proxy
chmod +x gh-proxy
./gh-proxy --addr :8080 --upstream https://github.com
```

本机配置代理：
```bash
export https_proxy=http://<ECS_IP>:8080 http_proxy=http://<ECS_IP>:8080
git config --global http.proxy http://<ECS_IP>:8080
```

优点：完全可控，覆盖所有 GitHub 资源；缺点：只能解决 GitHub，其他外网服务不覆盖。

## 三、付费机场订阅

- V2EX / 知乎搜"机场推荐 2025 2026"找近期活跃评测
- 优先选**日本节点**（延迟最低 ~30-50ms）
- 月费参考：¥30-80/月（按流量或无限流量档）
- 选支持 7 天无理由退款的商家

## 四、可用性实测命令

```bash
# 测镜像可达性（5s 超时）
curl -sI --connect-timeout 5 "https://<MIRROR>/https://raw.githubusercontent.com/git/git/master/README.md" | head -1

# 测真实下载速度（小文件）
time curl -o /tmp/test.txt "https://<MIRROR>/https://raw.githubusercontent.com/git/git/master/README.md"
```

## 五、故障排除

- 如果 API `/meta` 可达但 clone/下载超时 → TCP 连接被阻断，需用代理/机场
- `gh` CLI 有时比 curl 更稳定（走不同的 TCP 路径）
- Git 配置代理：`git config --global http.extraProxy http://...`

## 六、参考文件

- `references/status-20261030.md` — 2026-10-30 实测镜像站状态清单