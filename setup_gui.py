"""py2app build script: .venv/bin/python setup_gui.py py2app"""
from glob import glob

from setuptools import setup

setup(
    name="Devin Token Monitor",
    app=["gui_entry.py"],
    data_files=["prices.json", ("dashboard_ui", sorted(glob("devin_token_monitor/dashboard_ui/*.*")))],
    options={
        "py2app": {
            "iconfile": "assets/dtm.icns",
            "argv_emulation": False,
            "packages": ["devin_token_monitor"],
            "includes": ["WebKit", "AppKit", "Foundation"],
            "plist": {
                "CFBundleName": "Devin Token Monitor",
                "CFBundleDisplayName": "Devin Token Monitor",
                "CFBundleIdentifier": "com.local.devin-token-monitor",
                "CFBundleShortVersionString": "0.4.3",
                "CFBundleVersion": "0.4.3",
                "LSMinimumSystemVersion": "12.0",
            },
        }
    },
    setup_requires=["py2app"],
)
