function renderDashboard(source, cspSource, nonce) {
  const bridge = `
const vscodeApi = acquireVsCodeApi();
window.__DTM_VSCODE__ = true;
window.__DTM_VSCODE_BRIDGE__ = { postMessage: message => vscodeApi.postMessage(message) };
window.addEventListener('message', event => {
  const message = event.data || {};
  if (message.type === 'snapshot' && typeof window.update === 'function') window.update(message.snapshot);
  else if (message.type === 'usageReport') window.showUsageReport(message.queryId, message.report, message.error);
  else if (message.type === 'body' && typeof window.showBody === 'function') window.showBody(message.rid, message.body || '');
  else if (message.type === 'error' && typeof window.toast === 'function') window.toast(message.message);
  else if (message.type === 'loginItem') {
    const control = document.getElementById('set-login');
    if (control) control.checked = Boolean(message.enabled);
  }
});`;
  let html = source
    .replace('<head>', `<head>\n<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: ${cspSource}; style-src 'unsafe-inline' ${cspSource}; script-src 'nonce-${nonce}'; font-src data: ${cspSource}; connect-src 'none'; object-src 'none'; base-uri 'none';">`)
    .replace('<style>', `<style nonce="${nonce}">`)
    .replace('<script>', `<script nonce="${nonce}">${bridge}\n</script>\n<script nonce="${nonce}">`);
  const end = html.lastIndexOf('</script>');
  if (end < 0) throw new Error('Dashboard script closing tag was not found.');
  html = html.slice(0, end) + "vscodeApi.postMessage({action:'ready'});\n" + html.slice(end);
  return html;
}

module.exports = { renderDashboard };
