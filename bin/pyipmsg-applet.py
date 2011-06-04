#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, logging, logging.config

def make_sure_exists(dirpath):
    try:
        os.mkdir(dirpath)
    except OSError:
        if not os.path.exists(dirpath):
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        filename="/tmp/ipmsg.log",
        filemode = 'w',
    )

    import os
    userdir = os.path.expanduser('~/.pyipmsg')
    make_sure_exists(userdir)
    make_sure_exists(os.path.join(userdir, 'rsa'))
    make_sure_exists(os.path.join(userdir, 'webshare'))

    from pyipmsg import applet
    applet.main()

