# -*- coding: utf-8 -*-

import socket, os, time
import SocketServer, SimpleHTTPServer
from multiprocessing import Process

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
        pshare = Process(target=self._serve, args=(sid, root))
        pshare.daemon = True
        pshare.start()

        return self.get_url(sid)

    def _serve(self, sid, root):
        httpd = self.shares.get(sid)
        if not httpd:
            return False

        os.chdir(root)
        httpd.serve_forever()

    def shutdown(self, sid):
        httpd = self.shares.get(sid)
        if not httpd:
            return False

        httpd.shutdown()

    def get_url(self, sid):
        httpd = self.shares.get(sid)
        if not httpd:
            return False

        return 'http://%s:%s' % (engine.host, httpd.server_address[1])
