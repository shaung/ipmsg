# -*- coding: utf-8 -*-

import socket, select, time

import ipmsg.consts as c
from ipmsg.config import settings
from ipmsg.packet import Packet

import logging, traceback
logger = logging.getLogger(__file__)

class NetworkError(Exception):
    pass

class Server:
    """
    the UDP server responsible for message io processing.
    """

    sock = None
    addr = ('', c.IPMSG_DEFAULT_PORT)
    dispatch_cb = lambda p: None

    def __init__(self, dispatch_cb=None):
        self.waiting = set([])
        self.paused = set([])
        self.sending = set([])
        self.done = set([])
        self.dispatch_cb = dispatch_cb or self.dummy_dispatcher

    def set_dispatcher(self, dispatch_cb):
        self.dispatch_cb = dispatch_cb

    def dummy_dispatcher(self, p):
        pass

    def is_serving(self):
        return self.sock

    def start(self, addr):
        if self.sock:
            return

        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(addr)

    def stop(self):
        if not self.sock:
            return

        self.sock.close()
        self.sock = None

    def require_serving(bad_rslt=False):
        def func(f, *args, **kws):
            def innerfunc(self, *args, **kws):
                return self.is_serving() and f(self, *args, **kws) or bad_rslt
            return innerfunc
        return func

    #@require_serving
    def send_immediate(self, raw, addr):
        self.sock.sendto(raw, addr)
        return True

    #@require_serving
    def send_reserve(self, packet, addr):
        if (packet, addr) in self.waiting:
            logger.debug('already in queue')
            return

        if packet.has_check_option():
            self.waiting.add((packet, addr))
            logger.debug('added to waiting queue')
        else:
            self.sending.add((packet, addr))
            logger.debug('added to sending queue')
        return True

    def check_waiting(self, packet, addr, type):
        self.waiting = set([(p, a) for (p, a) in self.waiting if str(p.cntr) != str(packet.msg) or not p.is_type(type)])

    def resend(self, (packet, addr)):
        if (packet, addr) in self.paused:
            packet.timestamp = time.time()
            self.waiting.add((packet, addr))
            self.paused.discard((packet, addr))

    @require_serving(bad_rslt=[])
    def update(self):
        r, w, e = select.select([self.sock], [self.sock], [], 0)

        for sk in r:
            data, (ip, port) = sk.recvfrom(c.UDP_DATA_LEN)
            try:
                p = Packet.parse(data, (ip, port))
            except:
                logger.debug(traceback.format_exc())
                pass
            else:
                self.dispatch_cb(p)

        if w:
            new_paused = set([(p, addr) for (p, addr) in self.waiting if p.age() > settings['send_timeout']])
            self.paused |= new_paused
            self.waiting = set(args for args in self.waiting if args not in self.paused)
            if self.paused:
                logger.debug('paused: ' + repr(self.paused))
            if self.waiting:
                logger.debug('waiting: ' + repr(self.waiting))

            for (p, addr) in [args for args in self.waiting if args not in self.paused]:
                self.sock.sendto(p.raw, addr)
            for (p, addr) in self.sending:
                self.sock.sendto(p.raw, addr)
            self.sending = set([])

            return new_paused
        return []

