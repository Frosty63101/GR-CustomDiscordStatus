from setuptools import setup
import os
import tkinter

APP = ['GR-CustomDiscordStatus.py']
DATA_FILES = [('config', ['config.json'])]

# Try to dynamically locate Tcl/Tk paths
try:
    tcl_dir = os.path.join(os.path.dirname(tkinter.__file__), 'tcl8.6')
    tk_dir = os.path.join(os.path.dirname(tkinter.__file__), 'tk8.6')
    if not os.path.exists(tcl_dir) or not os.path.exists(tk_dir):
        raise FileNotFoundError("Tcl/Tk not found in tkinter path")
except Exception:
    # Fallback: common macOS framework path
    tcl_dir = '/Library/Frameworks/Python.framework/Versions/3.11/lib/tcl8.6'
    tk_dir = '/Library/Frameworks/Python.framework/Versions/3.11/lib/tk8.6'

    if not os.path.exists(tcl_dir) or not os.path.exists(tk_dir):
        print(f"WARNING: Tcl/Tk frameworks not found at either standard or fallback locations.")
        print(f"Continuing without bundling Tcl/Tk — GUI will likely crash at runtime.")
        tcl_dir = None
        tk_dir = None

resource_list = ['config.json']
if tcl_dir and tk_dir:
    resource_list += [tcl_dir, tk_dir]

OPTIONS = {
    'argv_emulation': True,
    'packages': ['requests', 'bs4', 'pypresence', 'pystray'],
    'includes': ['PIL.Image', 'PIL.ImageDraw', 'tkinter'],
    'iconfile': 'icon.icns',
    'resources': resource_list,
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
