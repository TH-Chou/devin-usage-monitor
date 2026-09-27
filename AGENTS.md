# Project development

- Use the existing `.venv` and PyObjC/AppKit/WKWebView architecture. The desktop application does not require an HTTP server.
- Quick Python validation: `.venv/bin/python -m compileall -q devin_token_monitor setup_gui.py`.
- Validate the evaluated `dashboard.PAGE` JavaScript, not only the Python source string. Extract its script and pass it to `node --check` on stdin.
- Launch development UI with `.venv/bin/python -m devin_token_monitor.gui`. Native UI verification needs an NSApplication event loop, not just mocked DOM tests. Check data rendering, navigation, lazy request bodies, dark mode, and the 860x560 minimum window.
- Liquid Glass uses AppKit `NSGlassEffectView` when available, with NSVisualEffectView fallback on older systems. Glass controls belong inside its `contentView`. Native sidebar navigation and the page must stay synchronized through `navigateTo` and the `navigate` bridge message.
- The WKWebView fills the entire native shell to provide one continuous background. Reserve navigation space with `.native-shell .shell` padding, not a separate colored native sidebar background.
- Verify traffic-light button bounds and sidebar bounds in the same NSWindow coordinate space. Keep the top control region clear when resizing. Window-server bounds can represent a Stage Manager thumbnail; they alone do not prove the NSWindow has shrunk.
- Lazy body callback signature is `showBody(request_or_message_id, text)`. Keep response bodies out of periodic usage snapshots.
- Non-destructive isolated build: `.venv/bin/python setup_gui.py py2app --dist-dir dist/<new-name> --bdist-base build/<new-name>`. Choose unused directories. Existing build shell scripts remove/replace generated bundles and staging directories; obtain approval before using them on existing artifacts.
- Packaging metadata version in `setup_gui.py` and `devin_token_monitor.__version__` should match. App icon is the raster-generated `assets/dtm.icns`; UI-only changes should not alter it or reset system icon caches.
- VS Code extension verification: `cd vscode-extension && npm install && npm run test`; build a local VSIX with `npm run package`. Staging copies the shared Python core and evaluated dashboard into the VSIX; test it with an isolated editor profile when available.
