from setuptools import setup
import os

APP = ['GR-CustomDiscordStatus.py']
DATA_FILES = [
    ('', ['config.json']),
]
OPTIONS = {
    'argv_emulation': True,
    'packages': ['requests', 'bs4', 'pypresence', 'pystray'],
    'includes': ['PIL.Image', 'PIL.ImageDraw', 'tkinter'],
    'iconfile': 'icon.icns',  # Optional: If you want a dock icon
    'resources': ['config.json'],
    'plist': {
        'CFBundleName': 'GR-CustomDiscordStatus',
        'CFBundleDisplayName': 'GR-CustomDiscordStatus',
        'CFBundleIdentifier': 'com.frosty63.GoodreadsRPC',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True
    }
}

if __name__ == "__main__":
    setup(
        app=APP,
        name='GR-CustomDiscordStatus',
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )
