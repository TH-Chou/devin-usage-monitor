#!/bin/bash
# Package the built .app into dist/DevinTokenMonitor.dmg with an
# /Applications shortcut (standard drag-to-install UX).
set -e
cd "$(dirname "$0")"

APP="dist/Devin Token Monitor.app"
[ -d "$APP" ] || ./build_app.sh

STAGE="dist/dmg_stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

hdiutil create \
    -volname "Devin Token Monitor" \
    -srcfolder "$STAGE" \
    -ov -format UDZO \
    "dist/DevinTokenMonitor.dmg"

rm -rf "$STAGE"
echo "Built: dist/DevinTokenMonitor.dmg"
