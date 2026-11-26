const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { EventEmitter } = require('node:events');
const { PassThrough, Writable } = require('node:stream');

const extensionRoot = path.join(__dirname, '..');
const turn = () => new Promise(resolve => setImmediate(resolve));
const snapshot = { today: { cost: 1 }, settings: {}, meta: {} };

// Exercise the public commands and webview message boundary with a controllable child process.
function setup(t) {
  const workers = [], commands = new Map(), messages = [], config = { pricesPath: '/fixture-prices.json' };
  let configChanged, receive;
  function spawn() {
    const child = new EventEmitter();
    child.stdout = new PassThrough();
    child.stderr = new PassThrough();
    child.requests = [];
    child.stdin = new Writable({ write(line, _, done) { child.requests.push(JSON.parse(line)); done(); } });
    child.reply = (request, result, error) => child.stdout.write(JSON.stringify({ id: request.id,
      ok: !error, result, error }) + '\n');
    child.exit = () => { child.exitCode = 2; child.stdout.end(); child.emit('close', 2, null); };
    child.kill = () => { child.killed = true; child.exit(); };
    workers.push(child);
    return child;
  }
  const status = { show() {}, hide() {} };
  const panel = { visible: true, onDidDispose() {}, onDidChangeViewState() {},
    webview: { postMessage(m) { messages.push(m); }, onDidReceiveMessage(fn) { receive = fn; } } };
  const vscode = {
    StatusBarAlignment: { Right: 1 }, ViewColumn: { One: 1 },
    commands: { registerCommand(k, v) { commands.set(k, v); } },
    workspace: { getConfiguration: () => ({ get: (k, d) => config[k] ?? d }),
      onDidChangeConfiguration(fn) { configChanged = fn; } },
    window: { createOutputChannel: () => ({ appendLine() {}, append() {} }),
      createStatusBarItem: () => status, createWebviewPanel: () => panel,
      showErrorMessage() {} },
  };
  const mod = { exports: {} };
  const source = fs.readFileSync(path.join(extensionRoot, 'extension.js'), 'utf8');
  vm.runInNewContext(source, { module: mod, require: id => {
    if (id === 'vscode') return vscode;
    if (id === 'node:child_process') return { spawn };
    if (id === './webview') return { renderDashboard: () => '' };
    if (id === 'node:fs') return { ...fs, readFileSync: () => '<html></html>' };
    return require(id);
  }, process, setTimeout, clearTimeout, setInterval, clearInterval, Buffer });
  mod.exports.activate({ subscriptions: [], extensionPath: extensionRoot, globalState: new Map() });
  t.after(() => mod.exports.deactivate());
  return { workers, messages, status, run: name => commands.get('devinTokenMonitor.' + name)(),
    receive: message => receive(message),
    configure(value) { config.databasePath = value;
      configChanged({ affectsConfiguration: key => key === 'devinTokenMonitor.databasePath' }); } };
}

test('refresh recovers after an unexpected worker exit', async t => {
  const host = setup(t), first = host.workers[0];
  first.exit();
  await turn();
  const done = host.run('refresh');
  assert.equal(host.workers.length, 2);
  const next = host.workers[1];
  next.reply(next.requests.at(-1), { summary: snapshot });
  await done;
});

test('a configuration change replaces a worker that is still initializing', async t => {
  const host = setup(t);
  host.configure('/fixture-A.db');
  host.configure('/fixture-B.db');
  assert.equal(host.workers.length, 3);
  const latest = host.workers[2];
  latest.reply(latest.requests.at(-1), { summary: snapshot });
  await turn();
});

test('request body errors settle the correct expanded row', async t => {
  const host = setup(t), worker = host.workers[0];
  await host.run('openDashboard');
  const done = host.receive({ action: 'getBody', rid: 'r1', mid: 'm1' });
  worker.reply(worker.requests.at(-1), null, 'Could not read the response');
  await done;
  const message = host.messages.find(item => item.type === 'body' && item.rid === 'r1');
  assert.equal(message?.error, 'Could not read the response');
});

test('fragmented and interleaved replies keep their original request IDs', async t => {
  const host = setup(t), worker = host.workers[0];
  await host.run('openDashboard');
  const first = host.receive({ action: 'getBody', rid: 'r-1' });
  const second = host.receive({ action: 'getBody', rid: 'r-2' });
  const [a, b] = worker.requests.slice(-2);
  const line = Buffer.from(JSON.stringify({ id: b.id, ok: true, result: { body: 'цена' } }) + '\n');
  const split = line.indexOf(Buffer.from('ц')) + 1;
  worker.stdout.write(line.subarray(0, split));
  worker.stdout.write(line.subarray(split));
  worker.reply(a, {body:'A'});
  await Promise.all([first, second]);
  assert.deepEqual(host.messages.filter(m => m.type === 'body').map(m => [m.rid, m.body]),
    [['r-2', 'цена'], ['r-1', 'A']]);
});

test('a malformed worker frame marks the dashboard offline and releases pending requests', async t => {
  const host = setup(t), worker = host.workers[0];
  await host.run('openDashboard');
  const done = host.receive({action:'ready'});
  worker.stdout.write('null\n');
  await done;
  assert.ok(worker.killed);
  assert.ok(host.messages.some(message => message.type === 'sourceError'));
});

test('old body and report requests cannot update a changed database', async t => {
  const host = setup(t);
  await host.run('openDashboard');
  const body = host.receive({action:'getBody', rid:'shared-id'});
  const report = host.receive({action:'usageReport', queryId:1});
  host.configure('/fixture-new.db');
  await Promise.all([body, report]);
  assert.equal(host.messages.filter(message => ['body', 'usageReport'].includes(message.type)).length, 0);
});

test('status displays microdollar costs and undefined cache share correctly', async t => {
  const host = setup(t), worker = host.workers[0];
  worker.reply(worker.requests[0], {summary:{...snapshot, today:{cost:0.00000042}}});
  await turn();
  assert.match(host.status.text,/0\.00000042/);
  assert.match(host.status.tooltip,/Cache read share: —/);
});

test('a budget save is acknowledged only after the worker confirms it', async t => {
  const host = setup(t), worker = host.workers[0];
  await host.run('openDashboard');
  const done = host.receive({action:'setBudget',value:2.75});
  assert.equal(host.messages.length, 0);
  worker.reply(worker.requests.at(-1), {snapshot:{...snapshot,settings:{daily_budget:2.75}}});
  await done;
  assert.equal(host.messages.find(message=>message.type==='budgetSaved').value,2.75);
});
