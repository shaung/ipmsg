# -*- coding: utf-8 -*-

import os, time, socket, logging

from ipmsg import consts as c
from ipmsg.packet import Packet
from ipmsg import util
from ipmsg.config import settings
from ipmsg.message.server import Server

logger = logging.getLogger(__file__)

class NetworkError(Exception):
    pass

class Engine:
    contacts = {}
    server = Server()

    def __init__(self):
        self.notify_callback = None
        self.nics = {}
        self.ip = ''
        self.port = c.IPMSG_DEFAULT_PORT
        self._update()
        self._init_cntr()
        self.block_ips = settings['block_list']

    def check_server_avalibility(self):
        try:
            self.start_server()
        except socket.error:
            return False

        try:
            raw = self.make_raw(tag=0)
            self.server.send_immediate(raw, ('<broadcast>', self.port))
        except socket.error:
            logger.debug('server start failed')
            return False
        else:
            return True

    def start_server(self):
        try:
            self.server.start(self.get_addr())
        except socket.error:
            logger.debug('server start failed')
            raise NetworkError

    def stop_server(self):
        self.server.stop()

    def get_addr(self):
        return self.ip, self.port

    def is_self(self, addr):
        return addr[1] == self.port and addr[0] in self.nics.values()

    def get_contacts(self):
        return self.contacts

    def get_contact(self, addr):
        return self.contacts.get(addr, None)

    def get_or_create_contact(self, p):
        for k in settings['group_list']:
            logger.debug('orginal group:-%s-' % k)
        if p.group and p.group not in settings['group_list']:
            logger.debug('new group:-%s-' % p.group)
            settings['group_list'].append(p.group)
        contact = self.get_contact(p.addr)
        if not contact:
            contact = p.extract_contact()
            if not contact.temporary:
                self.add_contact(contact)
                logger.debug('++ add new contact:%s,%s' % (contact.get_desc(), ':'.join(map(str, p.addr))))
            self.request_version(p.addr)

        if p.is_status_notify():
            if contact.has_left_for() > 0:
                self.request_version(p.addr)
            contact.name, contact.group = p.msg, p.group
            if p.test(c.IPMSG_ABSENCEOPT):
                contact.afk()
            else:
                contact.back()

        return contact

    def add_contact_list(self, p):
        pass
        """
        for contact in p.extract_contact_list():
            if not self.contacts.has_key(contact.addr):
                self.add_contact(contact)
        """

    def request_version(self, addr):
        tag = c.IPMSG_GETINFO
        self.send(addr, tag)

    def add_contact(self, contact):
        self.contacts[contact.addr] = contact

    def supports_utf8(self, addr):
        (ip, port) = addr
        if self.is_self(addr):
            return True
        if addr in self.contacts:
            return (port == self.port and ip in self.nics.values()) or self.contacts[addr].supports_utf8()
        else:
            return False

    def _get_stat_msg(self, fmt='%s'):
        if settings['use_status_as_group']:
            msg = ''
        else:
            msg = settings['stat_msg'][1]

        return msg and fmt % settings['stat_msg'][1] or ''

    def get_name(self):
        return settings['user_name'] or self.login

    def get_name_ext(self):
        return self.get_name() + self._get_stat_msg('[%s]')

    def _update(self):
        self.login = os.getenv('LOGNAME')
        self.host = socket.gethostname()

    def _init_cntr(self):
        # generate initial counter to avoid recording it everytime
        # be aware that the original ipmsg uses signed int for counter, so the value should be smaller than 2^31-1
        # here we use the seconds since the epoch, and substract it with some constant value
        self.cntr = long(time.time()) - 946080000

    def _inc_cntr(self):
        self.cntr += 1

    def make_raw(self, tag, msg=''):
        self._inc_cntr()
        raw = "%s:%s:%s:%s:" % (c.IPMSG_VERSION, self.cntr, self.login, self.host)
        raw += "%s:%s\0" % (tag, msg)
        return raw

    def make_msg(self, addr, tag, msg=''):
        extra = ''
        if tag & 0xFF in (c.IPMSG_BR_ENTRY, c.IPMSG_ANSENTRY, c.IPMSG_BR_ABSENCE):
            if settings['use_status_as_group']:
                gname = settings['stat_msg'][1]
            else:
                gname = settings['group_name']
            if gname:
                if tag & c.IPMSG_UTF8OPT or self.supports_utf8(addr):
                    tag |= c.IPMSG_UTF8OPT
                    extra = "%s\0" % gname
                else:
                    extra = "%s\0" % util.utf8_to_sjis(gname)
        raw = self.make_raw(tag, msg)
        logger.debug('make msg:' + raw)
        return raw + extra

    def send_packet(self, packet):
        logger.debug('send packet: %s' % (repr(packet)))
        self.server.send_reserve(packet, packet.addr)
        logger.debug('sent packet')

    def send(self, addr, tag = 0, msg = ''):
        raw = self.make_msg(addr, tag, msg)
        p = Packet.parse(raw, addr)
        self.server.send_reserve(p, addr)

    def send_to(self, contact, tag = 0, msg = ''):
        raw = self.make_msg(addr, tag, msg)
        p = Packet.parse(raw, contact.addr)
        self.server.send_reserve(p, contact.addr)

    def get_list(self, ip, port=None):
        tag = c.IPMSG_GETLIST
        raw = self.make_raw(tag, '')
        self.server.send_immediate(raw, (ip, port or self.port))

    def hello(self, addr, is_afk=False, is_secret=False):
        tag = c.IPMSG_BR_ENTRY | c.IPMSG_FILEATTACHOPT | c.IPMSG_ENCRYPTOPT
        if is_secret:
            tag |= c.IPMSG_NOADDLISTOPT
        if is_afk:
            tag |= c.IPMSG_ABSENCEOPT
        msg = self.get_name_ext()
        if self.supports_utf8(addr) or settings['always_use_utf8']:
            tag |= c.IPMSG_UTF8OPT
        else:
            msg = util.utf8_to_sjis(msg)
        raw = self.make_msg(addr, tag, msg)
        self.server.send_immediate(raw, addr)
        if not is_secret:
            self.notify_status(addr, is_afk)

    def broadcast_addrs(self):
        ips = ['<broadcast>'] + settings['include_list']
        return zip(ips, [self.port,] * len(ips))

    def helloall(self, is_afk=False, is_secret=False):
        raw = self.make_raw(tag=0)
        self.server.send_immediate(raw, ('<broadcast>', self.port))

        if not is_secret:
            self.notify_callback = lambda addr: addr[0] not in self.block_ips and self.notify_status(addr, is_afk) or None

        for addr in self.get_all_notify_addrs():
            self.hello(addr, is_afk=is_afk, is_secret=is_secret)

        self.block_all()

    def get_block_ips(self):
        all_blocked = [util.expand_ip(ip) for ip in settings['block_list']]
        if all_blocked:
            return [ip for ip in reduce((lambda x, y : x + y), all_blocked) if not self.is_self((ip, self.port))]
        else:
            return []

    def update_block_list(self):
        old = self.block_ips[:]
        self.block_ips = self.get_block_ips()
        for ip in [ip for ip in old if ip not in self.block_ips]:
            self.notify_callback((ip, self.port))
        for ip in [ip for ip in self.block_ips if ip not in old]:
            self.block(ip)

    def block(self, ip):
        raw = self.make_raw(c.IPMSG_BR_EXIT)
        self.server.send_immediate(raw, (ip, self.port))

    def block_all(self):
        for ip in self.block_ips:
            self.block(ip)

    def bye(self):
        tag = c.IPMSG_BR_EXIT
        raw = self.make_raw(tag)
        for addr in self.broadcast_addrs():
            self.server.send_immediate(raw, addr)

    def notify_status(self, addr, is_afk=True):
        tag = c.IPMSG_BR_ABSENCE | c.IPMSG_FILEATTACHOPT | c.IPMSG_ENCRYPTOPT
        if is_afk:
            tag |= c.IPMSG_ABSENCEOPT
        msg = self.get_name_ext()
        if self.supports_utf8(addr) or settings['always_use_utf8']:
            tag |= c.IPMSG_UTF8OPT
        else:
            msg = util.utf8_to_sjis(msg)
        raw = self.make_msg(addr, tag, msg)
        self.server.send_immediate(raw, addr)

    def notify_status_all(self, is_afk=True):
        for addr in self.get_all_notify_addrs():
            self.notify_status(addr, is_afk=is_afk)

        self.block_all()

    def get_all_notify_addrs(self):
        return self.broadcast_addrs() + [addr for addr in self.contacts]
 
engine = Engine()

