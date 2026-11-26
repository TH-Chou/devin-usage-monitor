const vscode = require('vscode');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const readline = require('node:readline');
const { renderDashboard } = require('./webview');
const { spawn } = require('node:child_process');

const PREFIX = 'devinTokenMonitor';

class PythonWorker {
  constructor(context, output) {
    this.context = context;
    this.output = output;
    this.pending = new Map();
    this.nextId = 1;
    this.child = this.start();
  }

  start() {
    const config = vscode.workspace.getConfiguration(PREFIX);
    const configured = config.get('pythonPath', '').trim();
    const command = configured || (process.platform === 'win32' ? 'python' : 'python3');
    const env = { ...process.env };
    const databasePath = config.get('databasePath', '').trim();
    const pricesPath = resolvePricesPath(this.context, config.get('pricesPath', '').trim());
    env.DTM_PRICES = pricesPath;
    if (databasePath) env.DEVIN_SESSIONS_DB = expandPath(databasePath);
    const script = path.join(this.context.extensionPath, 'python', 'worker.py');
    const child = spawn(command, [script], {
      cwd: this.context.extensionPath,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    const lines = readline.createInterface({ input: child.stdout });
    lines.on('line', line => {
      let message;
      try {
        message = JSON.parse(line);
        if (!message || !Number.isSafeInteger(message.id) || typeof message.ok !== 'boolean') {
          throw new Error('Missing request ID or response status');
        }
      } catch (error) {
        this.dispose(new Error(`Invalid Python worker response: ${error.message}`));
        return;
      }
      const pending = this.pending.get(message.id);
      if (!pending) return;
      clearTimeout(pending.timer);
      this.pending.delete(message.id);
      if (message.ok) pending.resolve(message.result);
      else pending.reject(new Error(message.error || 'Python worker failed'));
    });
    child.stderr.on('data', data => this.output.append(data.toString()));
    child.stdin.on('error', error => this.dispose(error));
    child.on('error', error => this.failAll(error));
    child.on('close', (code, signal) => {
      this.failAll(new Error(`Python worker exited (${signal || code})`));
    });
    return child;
  }

  request(action, fields = {}) {
    if (this.stopped) {
      return Promise.reject(this.stopped);
    }
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.dispose(new Error(`Python worker timed out during ${action}`));
      }, 120000);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(`${JSON.stringify({ id, action, ...fields })}\n`, error => {
        if (!error) return;
        clearTimeout(timer);
        this.pending.delete(id);
        reject(error);
      });
    });
  }

  failAll(error) {
    this.stopped ??= error;
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  dispose(error = new Error('Python worker stopped')) {
    this.failAll(error);
    if (this.child && !this.child.killed && this.child.exitCode == null) this.child.kill();
  }
}

let output;
let backend;
let panel;
let statusItem;
let lastSnapshot;
let lastStatus;
let lastLoggedError;
let pollTimer;
let polling = false;
let extensionContext;
let backendConfigKey;

function expandPath(value) {
  let result = value.replace(/^~(?=$|[\\/])/, os.homedir());
  result = result.replace(/\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?/g,
    (_match, name) => process.env[name] || '');
  if (process.platform === 'win32') {
    result = result.replace(/%([A-Za-z_][A-Za-z0-9_]*)%/g,
      (_match, name) => process.env[name] || '');
  }
  return path.resolve(result);
}

function resolvePricesPath(context, configured) {
  if (configured) return expandPath(configured);
  const shared = path.join(os.homedir(), '.devin-token-monitor', 'prices.json');
  if (fs.existsSync(shared)) return shared;
  const storage = context.globalStorageUri.fsPath;
  const target = path.join(storage, 'prices.json');
  fs.mkdirSync(storage, { recursive: true });
  if (!fs.existsSync(target)) {
    const bundled = path.join(context.extensionPath, 'python', 'prices.json');
    if (!fs.existsSync(bundled)) {
      throw new Error('Bundled prices.json is missing. Run npm run stage before launching the extension.');
    }
    fs.copyFileSync(bundled, target);
  }
  return target;
}

function formatCost(value) {
  if (!Number.isFinite(value)) return '—';
  if (value === 0) return '$0.00';
  const amount = Math.abs(value);
  const digits = amount >= 1 ? 2 : Math.min(12, Math.max(4, 1 - Math.floor(Math.log10(amount))));
  return (value < 0 ? '−$' : '$') + amount.toLocaleString('en-US', {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  });
}

function dayKey() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function logError(context, error) {
  const message = error instanceof Error ? error.message : String(error);
  if (lastLoggedError !== message) output.appendLine(message);
  lastLoggedError = message;
  if (statusItem) {
    statusItem.text = '$(warning) Devin Monitor';
    statusItem.tooltip = `${message}\nRun “Devin Token Monitor: Select Sessions Database” to configure the local Devin database.`;
  }
  if (context.notify) vscode.window.showErrorMessage(message);
}

function updateStatus(data, checkBudget = true) {
  lastStatus = data;
  const today = data.today || {};
  const cost = Number(today.cost || 0);
  const pollError = (data.meta || {}).poll_error;
  if (!pollError) lastLoggedError = undefined;
  const config = vscode.workspace.getConfiguration(PREFIX);
  const short = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });
  const requests = today.requests || 0;
  const tokens = today.total || 0;
  const input = (today.input || 0) + (today.cache_read || 0);
  const hit = input ? Math.round(100 * (today.cache_read || 0) / input) + '%' : '—';
  const metrics = { cost: formatCost(cost), tokens: short.format(tokens) + ' tok',
    requests: short.format(requests) + ' req', cache: hit + ' cache' };
  const selected = metrics[config.get('statusBarMetric', 'cost')] || metrics.cost;
  statusItem.text = pollError ? '$(warning) Devin Monitor' : `$(pulse) Devin ${selected}`;
  statusItem.tooltip = pollError
    ? `Devin Token Monitor\n${pollError}\nSelect the sessions database to retry`
    : `Devin Token Monitor\nToday: ${formatCost(cost)} · ${requests} requests · ${tokens.toLocaleString()} tokens\nCache read share: ${hit}\nClick to open dashboard`;
  if (config.get('showStatusBar', true)) statusItem.show();
  else statusItem.hide();
  const budget = Number((data.settings || {}).daily_budget || 0);
  if (checkBudget && !pollError && budget > 0 && cost > budget) {
    const key = `${PREFIX}.budgetAlertDay`;
    if (contextState && contextState.get(key) !== dayKey()) {
      contextState.update(key, dayKey());
      vscode.window.showWarningMessage(
        `Devin Token Monitor: today's estimated cost ${formatCost(cost)} exceeded the ${formatCost(budget)} daily budget.`,
      );
    }
  }
}

function showSnapshot(snapshot) {
  lastSnapshot = snapshot;
  updateStatus(snapshot);
  if (panel && panel.visible) panel.webview.postMessage({ type: 'snapshot', snapshot });
}

function showSummary(summary) {
  updateStatus(summary);
}

let contextState;

async function refresh(action = 'poll', notify = false) {
  if (!extensionContext) return;
  let worker;
  try {
    if (!backend || backend.stopped) {
      backend = undefined;
      backend = new PythonWorker(extensionContext, output);
      backendConfigKey = currentBackendConfig();
    }
    worker = backend;
    const includeSnapshot = Boolean(panel && panel.visible);
    const result = await worker.request(action, { include_snapshot: includeSnapshot });
    if (worker !== backend) return;
    if (result.snapshot) showSnapshot(result.snapshot);
    else if (result.summary) showSummary(result.summary);
    if (result.error) {
      if (lastLoggedError !== result.error) output.appendLine(result.error);
      lastLoggedError = result.error;
      if (notify) vscode.window.showErrorMessage(result.error);
    }
  } catch (error) {
    if (worker !== backend) return;
    logError({ notify }, error);
    if (panel) panel.webview.postMessage({ type: 'sourceError', message: error.message });
    throw error;
  }
}

function dashboardHtml(webview, context) {
  const nonce = crypto.randomBytes(18).toString('base64');
  const source = fs.readFileSync(path.join(context.extensionPath, 'media', 'dashboard.html'), 'utf8');
  return renderDashboard(source, webview.cspSource, nonce);
}

async function openPrices() {
  const result = await backend.request('pricesPath');
  const document = await vscode.workspace.openTextDocument(vscode.Uri.file(result.path));
  await vscode.window.showTextDocument(document);
}

async function exportCsv() {
  const uri = await vscode.window.showSaveDialog({
    defaultUri: vscode.Uri.file(path.join(os.homedir(), `devin-usage-${dayKey()}.zip`)),
    filters: { 'ZIP archive': ['zip'] },
    saveLabel: 'Export usage CSVs',
  });
  if (!uri) return;
  const result = await backend.request('export');
  await vscode.workspace.fs.writeFile(uri, Buffer.from(result.data, 'base64'));
  vscode.window.showInformationMessage(`Usage data exported to ${uri.fsPath}`);
}

async function handleWebviewMessage(message) {
  if (!message || !message.action) return;
  const target = panel;
  const worker = backend;
  const current = () => target && panel === target && worker === backend;
  try {
    if (message.action === 'ready') {
      if (lastSnapshot && panel) panel.webview.postMessage({ type: 'snapshot', snapshot: lastSnapshot });
      await refresh('poll');
    } else if (message.action === 'refresh') {
      await refresh('refresh', true);
    } else if (message.action === 'usageReport') {
      if (!target) return;
      try {
        if (!worker) throw new Error('Python worker is unavailable');
        const { report } = await worker.request('usageReport', {
          start: message.start, end: message.end, model: message.model,
        });
        if (current()) target.webview.postMessage({ type: 'usageReport', queryId: message.queryId, report });
      } catch (error) {
        if (current()) target.webview.postMessage({ type: 'usageReport', queryId: message.queryId, error: error.message });
      }
    } else if (message.action === 'getBody') {
      const rid = message.rid || message.mid || '';
      try {
        if (!worker) throw new Error('Python worker is unavailable');
        const { body } = await worker.request('body', { request_id: message.rid || '', message_id: message.mid || '' });
        if (current()) target.webview.postMessage({ type: 'body', rid, body });
      } catch (error) {
        if (current()) target.webview.postMessage({ type: 'body', rid, error: error.message });
      }
    } else if (message.action === 'setBudget') {
      if (!Number.isFinite(message.value) || message.value < 0) throw new Error('Enter a valid nonnegative budget.');
      const result = await worker.request('settings', { settings: { daily_budget: message.value } });
      if (current()) {
        showSnapshot(result.snapshot);
        target.webview.postMessage({ type: 'budgetSaved', value: result.snapshot.settings.daily_budget });
      }
    } else if (message.action === 'setLanguage') {
      const result = await backend.request('settings', { settings: { language: String(message.value || 'en') } });
      if (current()) showSnapshot(result.snapshot);
    } else if (message.action === 'setTheme') {
      const result = await backend.request('settings', { settings: { theme: String(message.value || 'system') } });
      if (current()) showSnapshot(result.snapshot);
    } else if (message.action === 'export') {
      await exportCsv();
    } else if (message.action === 'editPrices') {
      await openPrices();
    } else if (message.action === 'toggleLoginItem') {
      vscode.window.showInformationMessage('Automatic login startup is managed by your IDE for this extension.');
      if (panel) panel.webview.postMessage({ type: 'loginItem', enabled: false });
    } else if (message.action === 'jserr') {
      output.appendLine(`Dashboard JavaScript: ${message.msg}`);
    }
  } catch (error) {
    if (!current() || message.action === 'ready' || message.action === 'refresh') return;
    output.appendLine(error.message);
    target.webview.postMessage({ type: 'error', message: error.message });
  }
}

function openDashboard(context) {
  if (panel) {
    panel.reveal(vscode.ViewColumn.One);
    if (lastSnapshot) panel.webview.postMessage({ type: 'snapshot', snapshot: lastSnapshot });
    refresh('poll').catch(() => {});
    return;
  }
  panel = vscode.window.createWebviewPanel(
    'devinTokenMonitor.dashboard',
    'Devin Token Monitor',
    vscode.ViewColumn.One,
    { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] },
  );
  panel.webview.html = dashboardHtml(panel.webview, context);
  panel.webview.onDidReceiveMessage(handleWebviewMessage, undefined, context.subscriptions);
  panel.onDidChangeViewState(event => {
    if (event.webviewPanel.visible) refresh('poll').catch(() => {});
  }, undefined, context.subscriptions);
  panel.onDidDispose(() => { panel = undefined; }, undefined, context.subscriptions);
}

function currentBackendConfig() {
  const config = vscode.workspace.getConfiguration(PREFIX);
  return JSON.stringify([
    config.get('pythonPath', ''),
    config.get('databasePath', ''),
    config.get('pricesPath', ''),
  ]);
}

async function restartBackend(context) {
  if (backend && !backend.stopped && backendConfigKey === currentBackendConfig()) return;
  const previous = backend;
  backend = undefined;
  previous?.dispose();
  lastStatus = undefined;
  lastSnapshot = undefined;
  // A different database may reuse request IDs. Drop rows and outstanding body lookups together.
  if (panel) panel.webview.html = dashboardHtml(panel.webview, context);
  await refresh('initialize').catch(() => {});
}

function configurePolling() {
  if (pollTimer) clearInterval(pollTimer);
  const seconds = Math.max(5, Math.min(3600,
    Number(vscode.workspace.getConfiguration(PREFIX).get('refreshInterval', 15)) || 15));
  pollTimer = setInterval(() => {
    if (polling) return;
    polling = true;
    refresh('poll').catch(() => {}).finally(() => { polling = false; });
  }, seconds * 1000);
}

function activate(context) {
  contextState = context.globalState;
  output = vscode.window.createOutputChannel('Devin Token Monitor');
  context.subscriptions.push(output);
  extensionContext = context;
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 20);
  statusItem.command = 'devinTokenMonitor.openDashboard';
  statusItem.text = '$(pulse) Devin —';
  statusItem.tooltip = 'Open Devin Token Monitor';
  context.subscriptions.push(statusItem);
  if (vscode.workspace.getConfiguration(PREFIX).get('showStatusBar', true)) statusItem.show();

  context.subscriptions.push(
    vscode.commands.registerCommand('devinTokenMonitor.openDashboard', () => openDashboard(context)),
    vscode.commands.registerCommand('devinTokenMonitor.refresh', () => refresh('refresh', true).catch(() => {})),
    vscode.commands.registerCommand('devinTokenMonitor.openPrices', () => openPrices().catch(error => logError({ notify: true }, error))),
    vscode.commands.registerCommand('devinTokenMonitor.selectDatabase', async () => {
      const selected = await vscode.window.showOpenDialog({
        canSelectMany: false,
        openLabel: 'Select Devin sessions.db',
        filters: { 'SQLite database': ['db', 'sqlite', 'sqlite3'] },
      });
      if (!selected || !selected[0]) return;
      await vscode.workspace.getConfiguration(PREFIX).update(
        'databasePath', selected[0].fsPath, vscode.ConfigurationTarget.Global,
      );
      await restartBackend(context);
    }),
  );

  context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(event => {
    if (event.affectsConfiguration(`${PREFIX}.showStatusBar`)) {
      if (vscode.workspace.getConfiguration(PREFIX).get('showStatusBar', true)) statusItem.show();
      else statusItem.hide();
    }
    if (lastStatus && event.affectsConfiguration(`${PREFIX}.statusBarMetric`)) updateStatus(lastStatus, false);
    if (event.affectsConfiguration(`${PREFIX}.refreshInterval`)) configurePolling();
    if (event.affectsConfiguration(`${PREFIX}.pythonPath`) ||
        event.affectsConfiguration(`${PREFIX}.databasePath`) ||
        event.affectsConfiguration(`${PREFIX}.pricesPath`)) {
      restartBackend(context);
    }
  }));

  context.subscriptions.push({ dispose: () => { if (pollTimer) clearInterval(pollTimer); } });
  configurePolling();
  refresh('initialize').catch(() => {});
}

function deactivate() {
  if (pollTimer) clearInterval(pollTimer);
  extensionContext = undefined;
  const previous = backend;
  backend = undefined;
  previous?.dispose();
}

module.exports = { activate, deactivate };
