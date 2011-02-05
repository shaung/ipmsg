#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, logging, logging.config

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        filename="/tmp/ipmsg.log",
        filemode = 'w',
    )

    import os, os.path
    userdir = os.path.expanduser('~/.pyipmsg')
    # make sure the user dir exists
    try:
        os.mkdir(userdir)
    except OSError:
        if not os.path.exists(userdir):
            raise

    from pyipmsg import applet
    applet.main()

