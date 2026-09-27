const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');
const { renderDashboard } = require('../webview');

const source = fs.readFileSync(path.join(__dirname, '..', 'media', 'dashboard.html'), 'utf8');

test('dashboard themes and token insights are included', () => {
  for (const theme of ['midnight', 'graphite', 'paper', 'ocean', 'forest']) {
    assert.match(source, new RegExp(`data-theme=\\"${theme}\\"`));
    assert.match(source, new RegExp(`option value=\\"${theme}\\"`));
  }
  assert.match(source, /id="v-insights"/);
  assert.match(source, /id="analysis-percentiles"/);
  assert.match(source, /\.view#v-insights #analysis-kpis\{margin-bottom:20px\}/);
  assert.match(source, /month_projection/);
});

test('dashboard is adapted to a nonce-CSP VS Code Webview', () => {
  const html = renderDashboard(source, 'vscode-webview-resource:', 'testNonce123');
  assert.match(html, /script-src 'nonce-testNonce123'/);
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /window\.__DTM_VSCODE_BRIDGE__/);
  assert.match(html, /vscodeApi\.postMessage\(\{action:'ready'\}\)/);
  assert.match(html, /window\.update\(message\.snapshot\)/);
  assert.match(html, /window\.showBody\(message\.rid/);
  assert.doesNotMatch(html, /if\(native_\)document\.body\.classList\.add\('glass-app'\)/);
  assert.doesNotMatch(html, /<script>(?!<)/);

  const scripts = [...html.matchAll(/<script nonce="testNonce123">([\s\S]*?)<\/script>/g)];
  assert.equal(scripts.length, 2);
  for (const [, script] of scripts) {
    const result = spawnSync(process.execPath, ['--check'], { input: script, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  }
});
