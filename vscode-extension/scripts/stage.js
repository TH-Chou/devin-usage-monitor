const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const extensionRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(extensionRoot, '..');
const pythonRoot = path.join(extensionRoot, 'python');
const packagedCore = path.join(pythonRoot, 'devin_token_monitor');

fs.mkdirSync(packagedCore, { recursive: true });
for (const name of ['__init__.py', 'aggregator.py', 'db.py', 'exporter.py', 'pricing.py']) {
  fs.copyFileSync(
    path.join(repoRoot, 'devin_token_monitor', name),
    path.join(packagedCore, name),
  );
}
fs.copyFileSync(path.join(repoRoot, 'prices.json'), path.join(pythonRoot, 'prices.json'));
fs.copyFileSync(path.join(repoRoot, 'assets', 'icon_1024.png'), path.join(extensionRoot, 'media', 'icon.png'));
fs.copyFileSync(path.join(repoRoot, 'LICENSE'), path.join(extensionRoot, 'LICENSE'));

const py = process.env.DTM_BUILD_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const source = [
  'import sys',
  `sys.path.insert(0, ${JSON.stringify(repoRoot)})`,
  'from devin_token_monitor.dashboard import PAGE',
  `open(${JSON.stringify(path.join(extensionRoot, 'media', 'dashboard.html'))}, 'w', encoding='utf-8').write(PAGE)`,
].join('; ');
const result = spawnSync(py, ['-c', source], { cwd: repoRoot, encoding: 'utf8' });
if (result.error || result.status !== 0) {
  process.stderr.write(result.stderr || String(result.error));
  process.exit(result.status || 1);
}
console.log('Staged Python core, price table, icon, and dashboard HTML.');
