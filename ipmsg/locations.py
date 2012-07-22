# coding: utf-8

import os

basedir = os.path.expanduser('~/.ipmsg/')
rsadir = os.path.join(basedir, 'rsa')
websharedir = os.path.join(basedir, 'webshare')
config_file_path = os.path.join(basedir, 'ipmsg.conf')
log_file_path = os.path.join(basedir, 'ipmsg.log')

for path in (basedir, rsadir, websharedir):
    try:
        os.makedirs(os.path.join(basedir, path))
    except:
        pass


