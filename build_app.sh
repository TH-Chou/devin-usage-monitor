#!/bin/bash
# Build dist/Devin Token Monitor.app with py2app.
set -e
cd "$(dirname "$0")"
.venv/bin/python setup_gui.py py2app
if [ -d "dist/gui_entry.app" ]; then
    rm -rf "dist/Devin Token Monitor.app"
    mv "dist/gui_entry.app" "dist/Devin Token Monitor.app"
fi
echo "Built: dist/Devin Token Monitor.app"
