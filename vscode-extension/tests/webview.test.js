const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const { renderDashboard } = require('../webview');

const source = fs.readFileSync(path.join(__dirname, '..', 'media', 'dashboard.html'), 'utf8');

function readLocaleTables() {
  const start = source.indexOf('const LOCALE=');
  const end = source.indexOf('const t=k=>', start);
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  const code = `${source.slice(start, end)}\nglobalThis.localeTables = { LOCALE, OFFLINE_LABEL, I18N, EXTRA_I18N, DOWSL };`;
  const context = {};
  vm.runInNewContext(code, context);
  return context.localeTables;
}

test('day-over-day KPI is finite for zero and missing prior-day values', () => {
  const expression = source.match(/const dayOverDayDelta=([^;]+);/)[1];
  const delta = vm.runInNewContext(expression);
  assert.equal(delta(5, 10), -50);
  assert.equal(delta(0, 10), -100);
  assert.equal(delta(5, 0), null);
  assert.equal(delta(Number.NaN, 10), null);
  assert.match(source, /d\.by_day\.find\(day=>day\.day===dayKey\(yesterday\)\)/);
  assert.match(source, /dayOverDayDelta\(td\.cost\|\|0,yday\.cost\|\|0\)/);
});

test('dashboard themes and token insights are included', () => {
  for (const theme of ['midnight', 'graphite', 'paper', 'ocean', 'forest', 'porcelain', 'apricot', 'plum']) {
    assert.match(source, new RegExp(`data-theme=\\"${theme}\\"`));
    assert.match(source, new RegExp(`option value=\\"${theme}\\"`));
  }
  assert.match(source, /id="v-insights"/);
  assert.match(source, /id="analysis-percentiles"/);
  assert.match(source, /\.view#v-insights #analysis-kpis\{margin-bottom:20px\}/);
  assert.match(source, /month_projection/);
});

test('Russian dashboard locale covers all labels and placeholders', () => {
  const { LOCALE, OFFLINE_LABEL, I18N, EXTRA_I18N, DOWSL } = readLocaleTables();
  assert.equal(LOCALE.ru, 'ru-RU');
  assert.ok(OFFLINE_LABEL.ru);
  assert.deepEqual(Array.from(DOWSL.ru), ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']);
  assert.match(source, /data-lang="ru">Русский</);

  const english = { ...I18N.en, ...EXTRA_I18N.en };
  const russian = { ...I18N.ru, ...EXTRA_I18N.ru };
  for (const [key, text] of Object.entries(english)) {
    assert.equal(typeof russian[key], 'string', `missing Russian translation: ${key}`);
    assert.notEqual(russian[key].trim(), '', `empty Russian translation: ${key}`);
    const placeholders = value => (value.match(/\{[a-z]+\}/gi) || []).sort();
    assert.deepEqual(placeholders(russian[key]), placeholders(text), `placeholder mismatch: ${key}`);
  }
});

test('model drilldown and source health remain visible', () => {
  assert.match(source, /function setModelFilter\(m,[^)]*\)[\s\S]*?navigateTo\('requests'\)/);
  assert.doesNotMatch(source, /querySelectorAll\('nav a'\)\[3\]/);
  assert.match(source, /poll_error/);
});

test('dashboard is adapted to a nonce-CSP VS Code Webview', () => {
  const html = renderDashboard(source, 'vscode-webview-resource:', 'testNonce123');
  assert.match(html, /script-src 'nonce-testNonce123'/);
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /window\.__DTM_VSCODE_BRIDGE__/);
  assert.match(html, /vscodeApi\.postMessage\(\{action:'ready'\}\)/);
  assert.match(html, /window\.update\(message\.snapshot\)/);
  assert.match(html, /window\.showBody\(message\.rid/);
  assert.doesNotMatch(html, /<body class="native-shell"/);
  assert.doesNotMatch(html, /<script>(?!<)/);

  const scripts = [...html.matchAll(/<script nonce="testNonce123">([\s\S]*?)<\/script>/g)];
  assert.equal(scripts.length, 2);
  for (const [, script] of scripts) {
    const result = spawnSync(process.execPath, ['--check'], { input: script, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  }
});

test('inclusive reporting dates cross months, leap day, and DST boundaries', () => {
  const code = source.slice(source.indexOf('const reportDayMs='), source.indexOf('function syncReportModels'));
  const range = vm.runInNewContext(code + '\nreportRange');
  assert.equal(range('7d', '2024-03-04').start, '2024-02-27');
  assert.equal(range('30d', '2025-03-11').start, '2025-02-10');
  assert.equal(range('mtd', '2025-11-02').start, '2025-11-01');
  assert.equal(range('today', '2025-11-02').end, '2025-11-02');
  assert.equal(range('all', '2025-11-02').start, '');
});

test('requests can be found by ID and ranked by all four token classes', () => {
  const code = source.slice(source.indexOf('const reqDay='), source.indexOf('function toggleReq'));
  const base = {ts:'2026-11-26T12:00:00+08:00', model:'A', session_title:'Example',
    session_id:'test',input:1,output:1,cache_read:0,cache_creation:0};
  const reqs = [{...base,request_id:'Req-A',cost:2},{...base,request_id:'Req-B',cache_creation:5,cost:1}];
  const context = {DATA:{requests:reqs},filt:{sort:'tokens'},dayKey:()=>''};
  const rows = vm.runInNewContext(code + '\nfilteredReqs', context);
  assert.equal(rows()[0].request_id, 'Req-B');
  context.filt.sort='cost';
  assert.equal(rows()[0].request_id,'Req-A');
  context.filt.q='req-b';
  assert.equal(rows().length,1);
  assert.equal(rows()[0].request_id,'Req-B');
});

test('shared UI ships solid fills and supports reduced motion', () => {
  assert.doesNotMatch(source, /(?:linear|radial|conic)-gradient\s*\(|<(?:linear|radial)Gradient\b/i);
  assert.doesNotMatch(source, /backdrop-filter\s*:[^;}]*blur\(/i);
  assert.match(source, /prefers-reduced-motion/);
});

test('the extension manifest resolves to the staged extension artwork', () => {
  const extensionRoot = path.resolve(__dirname, '..');
  const { icon } = require('../package.json');
  const packaged = fs.readFileSync(path.join(extensionRoot, icon));
  const artwork = fs.readFileSync(path.join(extensionRoot, '..', 'assets', 'vsix-icon.png'));
  assert.deepEqual(packaged, artwork);
});

test('tiny positive costs remain distinct from zero', () => {
  const start = source.indexOf('function fmtCost(');
  const fmt = vm.runInNewContext(source.slice(start, source.indexOf('const fmtPrice=', start)) + '\nfmtCost');
  for (const cost of [2e-6, 1e-8, 1e-14]) {
    assert.equal(Number(fmt(cost).slice(1)), cost);
  }
  assert.equal(fmt(0), '$0.00');
});

test('report chart bins include idle dates, leap day and a partial final interval', () => {
  const start = source.indexOf('function buildReportBins');
  const bin = vm.runInNewContext(source.slice(start, source.indexOf('function drawReportTrend', start)) + '\nbuildReportBins', {
    reportDayMs: 86400000,
    isoDay: time => new Date(time).toISOString().slice(0, 10)
  });
  const rows = bin({start: '2024-02-27', end: '2024-03-02', daily: [
    {day: '2024-02-29', requests: 3}, {day: '2024-03-02', requests: 1}
  ]}, 'requests', 3);
  assert.deepEqual(Array.from(rows, row => [row.first, row.last, row.value]), [
    ['2024-02-27', '2024-02-28', 0], ['2024-02-29', '2024-03-01', 3], ['2024-03-02', '2024-03-02', 1]
  ]);
});
