#!/usr/bin/env python
# -*- coding = utf-8 -*-

import sys, logging, logging.config

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(message)s",
        filename="/tmp/ipmsg.log",
        filemode = 'w',
    )

    from pyipmsg import applet
    applet.main()

