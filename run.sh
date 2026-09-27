#!/bin/bash
# Launch the Devin token monitor menu bar app.
cd "$(dirname "$0")"
exec .venv/bin/python -m devin_token_monitor.app
