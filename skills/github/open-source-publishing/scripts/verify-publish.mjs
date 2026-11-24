#!/usr/bin/env node
/**
 * verify-publish.mjs — 开源发布 ad-hoc 验证模板(复制修改后运行,跑完删除)
 * 覆盖:tsc 编译 → 产物与线上 dist 对比(等价归一)→ 敏感扫描(白名单断言)→ 逻辑模拟
 * 用法:把 ROOT/LIVE/SENS 换成实际值;按项目增删断言。
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = '/path/to/project';            // 项目根目录
const LIVE = '/tmp/live-dist/dist';         // 线上 dist(如已 scp -r 拉取),无则置 null 跳过
const SENS = /your-email@example\.com|1\.2\.3\.4|your-domain\.top|BEGIN (RSA|OPENSSH|EC) PRIVATE|sk-[A-Za-z0-9]{20,}/i;
const ALLOWED_SENS_FILES = [/^README\.md$/]; // 刻意保留内容(在线体验链接等)白名单

let pass = 0, fail = 0;
const check = (name, cond, extra = '') => {
  if (cond) { pass++; console.log(`  ✅ ${name}${extra ? ' — ' + extra : ''}`); }
  else { fail++; console.log(`  ❌ ${name}${extra ? ' — ' + extra : ''}`); }
};

console.log('=== 1. 编译检查 ===');
try {
  const out = execSync(`cd ${ROOT} && npx tsc -p tsconfig.json 2>&1`, { encoding: 'utf8' });
  check('tsc 无错误', out.trim() === '', out.trim().slice(0, 150) || '(干净)');
} catch (e) {
  check('tsc 无错误', false, String(e.stderr || e.message).slice(0, 300));
}

console.log('=== 2. 本地产物 vs 线上 dist(等价归一后对比) ===');
if (LIVE && fs.existsSync(LIVE)) {
  // 等价归一:空串初始化↔undefined、单行 if↔带大括号、CRLF(按实际差异补充规则)
  const norm = (s) => s
    .replace(/\r/g, '')
    .replace(/let anonId = '';/g, 'let anonId;')
    .replace(/if \(x\) \{\n(\s*)y;\n\s*\}/g, 'if (x)\n$1y;');
  const diffs = [];
  for (const rel of fs.readdirSync(path.join(ROOT, 'dist'), { recursive: true }).filter((p) => p.endsWith('.js'))) {
    const l = path.join(ROOT, 'dist', rel), r = path.join(LIVE, rel);
    if (!fs.existsSync(r)) { diffs.push(`${rel}: 仅本地有`); continue; }
    if (norm(fs.readFileSync(l, 'utf8')) !== norm(fs.readFileSync(r, 'utf8'))) diffs.push(rel);
  }
  // 预期差异文件(如 config.js 的刻意占位)放白名单
  const unexpected = diffs.filter((d) => !['config.js'].includes(d));
  check('产物与线上逻辑一致', unexpected.length === 0, unexpected.join(', ') || '(全部一致)');
} else {
  check('产物对比', true, '无线上 dist,跳过(部署会话已验)');
}

console.log('=== 3. 敏感信息扫描(白名单断言) ===');
const hits = [];
const walk = (dir) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['node_modules', 'dist', '.git', '.DS_Store'].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p);
    else if (/\.(ts|tsx|js|mjs|md|json|conf|ps1|cmd|yml|yaml|html|css)$/.test(e.name)) {
      if (SENS.test(fs.readFileSync(p, 'utf8'))) hits.push(p.replace(ROOT + '/', ''));
    }
  }
};
walk(ROOT);
const allowed = hits.filter((h) => ALLOWED_SENS_FILES.some((re) => re.test(h)));
check('敏感零残留(白名单外)', hits.length === allowed.length, hits.filter((h) => !allowed.includes(h)).join(', ') || '(干净)');

console.log('=== 4. 逻辑模拟(等价行为断言,按项目写) ===');
// 例:身份复用判定
// check('重连携带 g1 → 复用', serverJoin('g1') === 'g1');

console.log(`\n结果: ${pass} 通过 / ${fail} 失败`);
process.exit(fail ? 1 : 0);
