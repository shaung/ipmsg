# -*- coding: utf-8 -*-

import socket, re, sys, os, os.path
import time, mmap, io
import SocketServer, SimpleHTTPServer
from multiprocessing import Process, Queue

from ipmsg.message import engine
from ipmsg.util import *

class WebShareServer:
    def __init__(self, path=None):
        self.shares= {}
        self.path = path or '/tmp/ipmsg/webshare'

    def _gen_webshare(self, attach):
        root = os.path.join(self.path, str(time.time()))
        os.makedirs(root)
        page = os.path.join(root, 'index.html')
        f = file(page, 'wb')
        f.write('-------- shared files --------\n')
        f.write('<br>' * 3)
        for att in attach:
            fname = os.path.basename(att)
            ln = os.path.join(root, fname)
            os.symlink(att, ln)
            f.write('<a href="%s">%s</a><br>\n' % (fname, fname))
        f.close()
        return root

    def prepare(self, attachments):
        root = self._gen_webshare(attachments)
        sid = time.time()
        httpd = SocketServer.TCPServer(('', 0), SimpleHTTPServer.SimpleHTTPRequestHandler)
        self.shares[sid] = httpd
        return sid, root

    def start(self, attachments):
        sid, root = self.prepare(attachments)
        pshare = Process(target=self._start, args=(sid, root))
        pshare.daemon = True
        pshare.start()

        return self.get_url(sid)

    def _start(self, sid, root):
        if not self.shares.has_key(sid):
            return False

        os.chdir(root)
        self.shares[sid].serve_forever()

    def shutdown(self, sid):
        if not self.shares.has_key(sid):
            return False

        self.shares[sid].shutdown()

    def get_url(self, sid):
        if not self.shares.has_key(sid):
            return ''

        return 'http://%s:%s' % (engine.host, self.shares[sid].server_address[1])

