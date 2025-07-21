from setuptools import setup

APP = ['GR-CustomDiscordStatus.py']
DATA_FILES = ['config.json']
OPTIONS = {
    'argv_emulation': True,
    'packages': ['requests', 'bs4', 'pypresence', 'PIL', 'pystray'],
    'includes': ['PIL.Image', 'PIL.ImageDraw'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
