#!/usr/bin/env node
/**
 * verify-locales.mjs — parity + runtime check for TypeScript i18n locale packs.
 *
 * Usage (from project root):
 *   node scripts/verify-locales.mjs                        # all *.ts in src/i18n/locales vs en.ts
 *   node scripts/verify-locales.mjs src/i18n/locales en.ts
 *   node scripts/verify-locales.mjs --runtime              # + bundle & import each dict via esbuild
 *
 * Per locale file it reports: key count, missing / extra keys, key ORDER vs base,
 * per-key placeholder mismatch ({n} {msg} {tag} {name} {online} {max} ...), duplicates,
 * empty values. --runtime additionally bundles each locale with the project's esbuild and
 * imports it in node, proving the object really evaluates (catches quoting/escape errors that
 * a regex scan cannot see, e.g. an unescaped apostrophe in fr/it).
 *
 * Read-only: never edits a locale file. Exit 1 on any failure.
 */
import { readFileSync, readdirSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { join, resolve, relative } from 'node:path';
import { execFileSync } from 'node:child_process';

const argv = process.argv.slice(2);
const runtime = argv.includes('--runtime');
const pos = argv.filter((a) => !a.startsWith('-'));
const dir = resolve(pos[0] ?? 'src/i18n/locales');
const baseName = pos[1] ?? 'en.ts';

// Matches:   'key': 'value',      (value may contain escaped chars: \' or \\)
const PAIR = /^\s*'((?:[^'\\]|\\.)*)'\s*:\s*'((?:[^'\\]|\\.)*)'\s*,?\s*$/gm;
const unescape = (s) => s.replace(/\\(['\\])/g, '$1');
const ph = (s) => (s.match(/\{[A-Za-z0-9_]+\}/g) ?? []).sort().join(',');

function parse(file) {
  const src = readFileSync(file, 'utf8');
  const entries = [];
  for (const m of src.matchAll(PAIR)) entries.push([m[1], unescape(m[2])]);
  const keys = [];
  const dups = [];
  const map = new Map();
  for (const [k, v] of entries) {
    if (map.has(k)) dups.push(k);
    else keys.push(k);
    map.set(k, v);
  }
  return { map, keys, dups };
}

const basePath = join(dir, baseName);
if (!existsSync(basePath)) {
  console.error(`base locale not found: ${basePath}`);
  process.exit(2);
}
const base = parse(basePath);
const files = readdirSync(dir).filter((f) => f.endsWith('.ts') && f !== baseName).sort();

console.log(`base ${baseName}: ${base.keys.length} keys, ${files.length} locale(s) to check\n`);

let failed = 0;
let warned = 0;
for (const f of files) {
  const cur = parse(join(dir, f));
  const missing = base.keys.filter((k) => !cur.map.has(k));
  const extra = cur.keys.filter((k) => !base.map.has(k));
  const orderOk = cur.keys.join('\u0000') === base.keys.join('\u0000');
  const badPh = base.keys.filter((k) => cur.map.has(k) && ph(base.map.get(k)) !== ph(cur.map.get(k)));
  const empty = cur.keys.filter((k) => !(cur.map.get(k) ?? '').trim());
  // Warning only (never fails the run): value byte-identical to the base. Brand nouns and
  // unit symbols legitimately match; prose that matches means English was pasted instead of
  // translated — the exact defect that survives every count/placeholder check and only a
  // native reader notices.
  const leak = base.keys.filter(
    (k) =>
      cur.map.has(k) &&
      cur.map.get(k) === base.map.get(k) &&
      !/\{[A-Za-z0-9_]+\}/.test(base.map.get(k)),
  );
  const bad = missing.length || extra.length || badPh.length || empty.length || cur.dups.length || !orderOk;
  if (!bad && leak.length) warned++;
  if (bad) failed++;
  const detail = [
    missing.length ? `missing=${missing.join(',')}` : '',
    extra.length ? `extra=${extra.join(',')}` : '',
    cur.dups.length ? `dup=${cur.dups.join(',')}` : '',
    orderOk ? '' : 'order!=base',
    badPh.length ? `ph=${badPh.join(',')}` : '',
    empty.length ? `empty=${empty.join(',')}` : '',
    leak.length ? `leak=${leak.join(',')}` : '',
  ].filter(Boolean).join(' ');
  console.log(`${bad ? 'FAIL' : leak.length ? 'WARN' : 'ok  '} ${f.padEnd(10)} keys=${cur.keys.length} ${detail}`);
}

if (runtime) {
  const bin = join(process.cwd(), 'node_modules', '.bin', 'esbuild');
  if (!existsSync(bin)) {
    console.log('\n[runtime] skipped — node_modules/.bin/esbuild missing (npm i -D esbuild)');
  } else {
    const tag = process.pid;
    const tmpIn = resolve(`.locale-verify.${tag}.mjs`);
    const tmpOut = resolve(`.locale-verify.${tag}.bundle.mjs`);
    const rel = (n) => './' + relative(process.cwd(), join(dir, n)).replace(/\\/g, '/');
    const entry = [
      `import base from '${rel(baseName)}';`,
      ...files.map((f, i) => `import l${i} from '${rel(f)}';`),
      `const dicts = { ${files.map((f, i) => `'${f}': l${i}`).join(', ')} };`,
      `const baseKeys = Object.keys(base);`,
      `const ph = (s) => (s.match(/\\{[A-Za-z0-9_]+\\}/g) || []).sort().join(',');`,
      `let ok = true;`,
      `for (const [f, d] of Object.entries(dicts)) {`,
      `  const keys = Object.keys(d);`,
      `  const missing = baseKeys.filter((k) => !(k in d)).length;`,
      `  const extra = keys.filter((k) => !(k in base)).length;`,
      `  const phBad = baseKeys.filter((k) => ph(base[k]) !== ph(d[k] ?? '')).length;`,
      `  const bad = missing || extra || phBad || keys.length !== baseKeys.length;`,
      `  if (bad) ok = false;`,
      `  console.log('[runtime] ' + f.padEnd(10) + ' keys=' + keys.length + ' missing=' + missing + ' extra=' + extra + ' ph=' + phBad + (bad ? ' FAIL' : ' ok'));`,
      `}`,
      `process.exit(ok ? 0 : 1);`,
    ].join('\n');

    writeFileSync(tmpIn, entry + '\n');
    try {
      execFileSync(
        bin,
        [tmpIn, '--bundle', '--platform=node', '--format=esm', '--loader:.ts=ts',
         '--outfile=' + tmpOut, '--log-level=warning'],
        { stdio: 'inherit' },
      );
      execFileSync(process.execPath, [tmpOut], { stdio: 'inherit' });
    } catch {
      failed++;
      console.error('[runtime] evaluation failed (syntax / escape error in a locale file)');
    } finally {
      rmSync(tmpIn, { force: true });
      rmSync(tmpOut, { force: true });
    }
  }
}

if (failed) {
  console.error(`\n${failed} check(s) failed`);
  process.exit(1);
}
if (warned) {
  console.log(
    `\nALL LOCALES PASS — ${warned} file(s) flagged leak= (values identical to the base).\n` +
      'Fine for brand nouns / unit symbols; for prose it means untranslated text would ship.',
  );
} else {
  console.log('\nALL LOCALES PASS');
}
