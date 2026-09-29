"""py2app build script: .venv/bin/python setup_gui.py py2app"""
from setuptools import setup

setup(
    name="Devin Token Monitor",
    app=["gui_entry.py"],
    data_files=["prices.json"],
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
                "CFBundleShortVersionString": "0.3.1",
                "CFBundleVersion": "0.3.1",
                "LSMinimumSystemVersion": "12.0",
            },
        }
    },
    setup_requires=["py2app"],
)
