"""
This is a setup.py script generated by py2applet
Usage:
    python setup.py py2app
"""

from setuptools import setup
import requests.certs
APP = ['pyfa.py']
DATA_FILES = ['eve.db', 'README.md', 'LICENSE', 'imgs', requests.certs.where()]
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'dist_assets/mac/pyfa.icns',
    'packages': ['eos', 'gui', 'gui_service', 'utils']
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
