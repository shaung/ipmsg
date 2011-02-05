#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path, glob

from setuptools import setup

__VERSION__ = '0.0.1.0'

def _expand(dest, src):
    import os, os.path
    dest = os.path.normpath(dest)
    rslt = [(dest, os.path.join(src, '*.*'))]
    base = os.path.abspath(src)
    for root, dirs, files in os.walk(src):
        for d in dirs:
            rel = os.path.relpath(root, base)
            destpath = os.path.normpath(os.path.join(dest, rel, d))
            srcpath = os.path.normpath(os.path.join(root, d, '*.*'))
            rslt.append((destpath, srcpath))
    return rslt

def glob_dir(dest_dir, src_dir):
    return [(dest, glob.glob(src)) for dest, src in _expand(dest_dir, src_dir)]

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
        ('/usr/lib/bonobo/servers', ['data/GNOME_Panel_Pyipmsg_Factory.server']),
    ] + glob_dir('/usr/share/pyipmsg/icons', 'data/icons'),
    'license': 'GPLv3',
    'download_url': '',
    'install_requires': [
        'M2Crypto',
        'PyCrypto',
    ],
}

setup(**params)
