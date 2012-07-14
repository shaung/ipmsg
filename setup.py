#!/usr/bin/env python
# coding: utf-8

import os

from distutils.core import setup

__VERSION__ = '0.1.0'

params = {
    'name': 'ipmsg',
    'version': __VERSION__,
    'description': 'IP Messenger for linux',
    'author': 'shaung',
    'author_email': '_@shaung.org',
    'url': 'http://github.com/shaung/ipmsg/',
    'packages':[
        'ipmsg',
        'ipmsg.message',
        'ipmsg.crypto',
        'ipmsg.share',
    ],
    'license': 'BSD',
    'download_url': 'https://github.com/shaung/ipmsg/tarball/master',
    'zip_safe': False,
    'classifiers': [
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    'install_requires': [line for line in open('requirements.txt')],
}

setup(**params)
