from setuptools import setup
import os
import tkinter

# Get Tcl/Tk paths
tcl_dir = os.path.join(os.path.dirname(tkinter.__file__), 'tcl8.6')
tk_dir = os.path.join(os.path.dirname(tkinter.__file__), 'tk8.6')

APP = ['GR-CustomDiscordStatus.py']
DATA_FILES = [
    ('', ['config.json']),
]

OPTIONS = {
    'argv_emulation': True,
    'packages': ['requests', 'bs4', 'pypresence', 'pystray'],
    'includes': ['PIL.Image', 'PIL.ImageDraw', 'tkinter'],
    'iconfile': 'icon.icns',
    'resources': [
        'config.json',
        tcl_dir,
        tk_dir
    ],
    'plist': {
        'CFBundleName': 'GR-CustomDiscordStatus',
        'CFBundleDisplayName': 'GR-CustomDiscordStatus',
        'CFBundleIdentifier': 'com.frosty63.GoodreadsRPC',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True
    }
}

setup(
    app=APP,
    name='GR-CustomDiscordStatus',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
