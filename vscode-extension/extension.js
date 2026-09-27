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
      } catch (error) {
        this.output.appendLine(`Invalid Python worker response: ${error.message}`);
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
    child.on('error', error => this.failAll(error));
    child.on('close', (code, signal) => {
      this.failAll(new Error(`Python worker exited (${signal || code})`));
    });
    return child;
  }

  request(action, fields = {}) {
    if (!this.child || this.child.killed) {
      return Promise.reject(new Error('Python worker is not running'));
    }
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Python worker timed out during ${action}`));
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
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  dispose() {
    this.failAll(new Error('Python worker stopped'));
    if (this.child && !this.child.killed) this.child.kill();
  }
}

let output;
let backend;
let panel;
let statusItem;
let lastSnapshot;
let lastLoggedError;
let pollTimer;
let polling = false;
let restarting = false;
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
  return value >= 1
    ? `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : `$${value.toFixed(4)}`;
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

function updateStatus(data) {
  const today = data.today || {};
  const cost = Number(today.cost || 0);
  const pollError = (data.meta || {}).poll_error;
  if (!pollError) lastLoggedError = undefined;
  statusItem.text = pollError ? '$(warning) Devin Monitor' : `$(pulse) Devin ${formatCost(cost)}`;
  statusItem.tooltip = pollError
    ? `Devin Token Monitor\n${pollError}\nSelect the sessions database to retry`
    : `Devin Token Monitor\nToday: ${formatCost(cost)} · ${today.requests || 0} requests\nClick to open dashboard`;
  const config = vscode.workspace.getConfiguration(PREFIX);
  if (config.get('showStatusBar', true)) statusItem.show();
  else statusItem.hide();
  const budget = Number((data.settings || {}).daily_budget || 0);
  if (!pollError && budget > 0 && cost > budget) {
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
  if (!backend) return;
  try {
    const includeSnapshot = Boolean(panel && panel.visible);
    const result = await backend.request(action, { include_snapshot: includeSnapshot });
    if (result.snapshot) showSnapshot(result.snapshot);
    else if (result.summary) showSummary(result.summary);
    if (result.error) throw new Error(result.error);
  } catch (error) {
    logError({ notify }, error);
    if (panel) panel.webview.postMessage({ type: 'error', message: error.message });
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
  try {
    if (message.action === 'ready') {
      if (lastSnapshot && panel) panel.webview.postMessage({ type: 'snapshot', snapshot: lastSnapshot });
      await refresh('poll');
    } else if (message.action === 'refresh') {
      await refresh('refresh', true);
    } else if (message.action === 'getBody') {
      const result = await backend.request('body', {
        request_id: message.rid || '',
        message_id: message.mid || '',
      });
      if (panel) panel.webview.postMessage({ type: 'body', rid: message.rid || message.mid || '', body: result.body });
    } else if (message.action === 'setBudget') {
      const result = await backend.request('settings', { settings: { daily_budget: Number(message.value) || 0 } });
      showSnapshot(result.snapshot);
    } else if (message.action === 'setLanguage') {
      const result = await backend.request('settings', { settings: { language: String(message.value || 'en') } });
      showSnapshot(result.snapshot);
    } else if (message.action === 'setTheme') {
      const result = await backend.request('settings', { settings: { theme: String(message.value || 'system') } });
      showSnapshot(result.snapshot);
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
    logError({ notify: false }, error);
    if (panel) panel.webview.postMessage({ type: 'error', message: error.message });
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

function createBackend(context) {
  try {
    const next = new PythonWorker(context, output);
    backendConfigKey = currentBackendConfig();
    return next;
  } catch (error) {
    logError({ notify: false }, error);
    return undefined;
  }
}

async function restartBackend(context) {
  if (restarting || (backend && backendConfigKey === currentBackendConfig())) return;
  restarting = true;
  try {
    if (backend) backend.dispose();
    lastSnapshot = undefined;
    backend = createBackend(context);
    if (!backend) return;
    await refresh('initialize');
  } catch (error) {
    logError({ notify: false }, error);
  } finally {
    restarting = false;
  }
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
  backend = createBackend(context);
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
  if (backend) backend.dispose();
}

module.exports = { activate, deactivate };
