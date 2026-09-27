# VS Code-family port: research and design

## Executive decision

A VSIX port is technically sound, but it should be a **desktop Node extension host + bundled Python worker + VS Code Webview**, not a wrapper around the macOS `.app` and not a localhost HTTP server. This preserves the existing SQLite ingestion, incremental aggregation, model pricing, request deduplication, lazy response bodies, CSV export, dashboard and six-language UI while replacing only the AppKit host.

The implementation is a VS Code-compatible desktop extension. Browser-only editors are deliberately out of scope; compatibility with individual VS Code forks depends on their extension policies and API version.

## Findings

### 1. Extension host and local data

VS Code separates Node.js extension hosts (local and remote) from the browser Web Extension Host. Browser extensions cannot spawn child processes. This monitor must launch Python and read a local SQLite file, so it is not a browser extension.

The manifest declares `extensionKind: ["ui"]`, preferring the local UI host. This makes the database lookup independent of whether the currently opened workspace is remote. In `vscode.dev` / `github.dev`, there is no supported local Node host for this extension, so the local database feature cannot work.

Python 3.10+ is required because the reused project modules use the Python 3.10 type syntax. The extension uses only Python's standard library; users do not need PyObjC, rumps, or pip-installed project dependencies. Python executable and SQLite database paths are configurable. macOS/Linux use the existing Devin CLI default path; other platforms can choose the actual database path in Settings or through the database picker.

### 2. Reusing the existing dashboard

The current dashboard is already a self-contained HTML/CSS/JavaScript page, and its existing action protocol covers refresh, settings, navigation, export, language changes and lazy body loading. The build stage extracts the evaluated `dashboard.PAGE` and packages the shared aggregator/pricing/database/exporter modules alongside it.

VS Code Webviews run in an isolated context and communicate with the extension by message passing. The extension supplies a small compatibility bridge for the existing `window.webkit.messageHandlers.dtm` contract. A generated nonce protects scripts with a Webview CSP; local resource roots are empty and network connections are denied. The AppKit-only drag affordance is not enabled in the IDE Webview.

A Webview is justified here because the product's core UI is a multi-chart, filterable dashboard, beyond the practical reach of status-bar/tree-only VS Code APIs. IDE-native commands, status-bar cost, database picker, file editing and save dialog remain VS Code APIs.

### 3. Backend transport

The extension starts a single bundled Python worker and exchanges newline-delimited JSON through stdio. It does not open a TCP port. The worker delegates to existing project modules and supports initialization/polling, settings updates, lazy body reads, active price-table lookup, and a ZIP containing the four CSV exports.

This boundary keeps the implementation portable and preserves the one source of truth for pricing and aggregation. The extension staging script copies only required Python modules and the public seed price table into the VSIX, avoiding runtime downloads or package installation.

### 4. VSIX and editor-fork distribution

The `.vsix` is the standard installable package produced by `@vscode/vsce`. It can be installed locally in VS Code with `code --install-extension <file.vsix>` or from the Extensions UI's **Install from VSIX…** action. Publishing and discovery are separate from VSIX packaging: VS Code Marketplace publishing requires a publisher account; Cursor's documentation says its third-party extensions use Open VSX and that not every Marketplace extension is listed there.

This project does not claim universal fork compatibility. A fork must support desktop Node extension hosts, the contributed VS Code APIs, Webviews, and manual VSIX installation or an appropriate marketplace. Cursor documents VSIX-compatible extension installs. Windsurf and other forks should be verified against the particular release and its current extension-install policy before claiming support. There is no `browser` entry point.

### 5. Privacy and safety

- SQLite is opened in read-only mode by the shared database module.
- Usage snapshots and response bodies travel only over local stdio and the editor's Webview message channel.
- No HTTP listener, analytics, telemetry, or external service is introduced.
- The active price table is editable user data; the bundled VSIX copy is not used as the writable settings store by default.
- The Webview cannot load network resources and has no access to arbitrary local files.

## Validation completed

- `npm run test`: stages shared source and passes an integration test using a temporary SQLite database; verifies aggregate totals, lazy body retrieval, and all four CSV files in the ZIP.
- Node syntax checks pass for the extension and build scripts.
- `npm run package`: produces a VSIX with the Python worker, shared aggregation/pricing modules, 142-model price table and dashboard HTML.

A real Extension Development Host interaction test remains necessary to verify rendering and command behavior in the user's chosen IDE. Webview APIs cannot be fully validated by running the JavaScript in Node alone.

## References

- [VS Code Webview API and security/CSP guidance](https://code.visualstudio.com/api/extension-guides/webview)
- [VS Code extension host locations and runtimes](https://code.visualstudio.com/api/advanced-topics/extension-host)
- [VS Code Web Extensions: browser-host limitations](https://code.visualstudio.com/api/extension-guides/web-extensions)
- [Authoring Python-backed VS Code extensions](https://code.visualstudio.com/api/advanced-topics/python-extension-template)
- [Packaging extensions as VSIX](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Cursor extension marketplace and compatibility](https://cursor.com/help/customization/extensions)
