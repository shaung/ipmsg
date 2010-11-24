#!/usr/bin/python
# vim:fileencoding=utf-8

import os.path, glob

from setuptools import setup

__VERSION__ = '0.0.1.0'

params = {
    'name': 'pyipmsg',
    'version': __VERSION__,
    'description': 'An ipmsg alternative for Gnome, written in python',
    'author': 'Shaung',
    'author_email': 'shaun.geng@gmail.com',
    'url': 'http://github.com/shaung/pyipmsg/',
    'scripts': [
        'pyipmsg-applet.py',
    ],
    'packages':[
        'ipmsg',
        'ipmsg.message',
        'ipmsg.crypto',
        'ipmsg.share',
        'pyipmsg',
        'pyipmsg.common',
        'pyipmsg.conf',
        'pyipmsg.dialogs',
        'pyipmsg.widgets',
    ],
    'data_files': [
        ('/usr/share/pyipmsg/icons', glob.glob('data/icons/*.png')),
        ('/usr/share/pyipmsg/icons/app', glob.glob('data/icons/app/*')),
        ('/usr/share/pyipmsg/icons/menu', glob.glob('data/icons/menu/*')),
        ('/usr/share/pyipmsg/icons/misc', glob.glob('data/icons/misc/*')),
        ('/usr/share/pyipmsg/icons/toolbar', glob.glob('data/icons/toolbar/*')),
        ('/usr/share/pyipmsg/icons/notify', glob.glob('data/icons/notify/*')),
        ('/usr/share/pyipmsg/icons/window', glob.glob('data/icons/window/*')),
        (os.path.expanduser('~/.pyipmsg'), ['data/global.conf']),
        ('/usr/lib/bonobo/servers', ['data/GNOME_Panel_Pyipmsg_Factory.server']),
    ],
    'license': 'GPLv3',
    'download_url': '',
    'install_requires': [
        'M2Crypto',
        'PyCrypto',
    ],
}

setup(**params)
