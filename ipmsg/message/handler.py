# -*- coding: utf-8 -*-

import socket, select
import sys, os, time, re
import logging
import traceback
from functools import wraps

from engine import engine

from ipmsg import consts as c
from ipmsg.config import settings
from ipmsg.crypto import cry
from ipmsg.share import upload_manager, WebShareServer
from ipmsg.packet import Packet, Attachment
from ipmsg.contact import Contact
from ipmsg import util
from ipmsg.util import shex
from ipmsg.status import status
from message import Message

logger = logging.getLogger(__file__)

class MessageHandler:
    def __init__(self):
        self.messages = []

        engine.server.set_dispatcher(self.dispatch_msg)

        self.command = { \
            # notice
            c.IPMSG_ANSENTRY        : self.rsps_ansentry, \
            c.IPMSG_BR_ENTRY        : self.rsps_entry, \
            c.IPMSG_BR_EXIT         : self.rsps_exit, \
            c.IPMSG_BR_ABSENCE      : self.rsps_absence, \
            # host list
            c.IPMSG_BR_ISGETLIST    : self.rsps_isgetlist, \
            c.IPMSG_OKGETLIST       : self.rsps_okgetlist, \
            c.IPMSG_GETLIST         : self.rsps_getlist, \
            c.IPMSG_ANSLIST         : self.rsps_anslist, \
            # message
            c.IPMSG_SENDMSG         : self.rsps_sendmsg, \
            c.IPMSG_RECVMSG         : self.rsps_recvmsg, \
            c.IPMSG_READMSG         : self.rsps_readmsg, \
            c.IPMSG_DELMSG          : self.rsps_delmsg, \
            c.IPMSG_ANSREADMSG      : self.rsps_ansreadmsg, \
            # version
            c.IPMSG_GETINFO         : self.rsps_getinfo, \
            c.IPMSG_SENDINFO        : self.rsps_sendinfo, \
            # status
            c.IPMSG_GETABSENCEINFO  : self.rsps_getabsenceinfo, \
            c.IPMSG_SENDABSENCEINFO : self.rsps_sendabsenceinfo, \
            # rsa key
            c.IPMSG_GETPUBKEY       : self.rsps_getpubkey, \
            c.IPMSG_ANSPUBKEY       : self.rsps_anspubkey, \
        }

    def send(self, addrs, msg, atts=[], **options):
        logger.debug('ready to send' + msg + repr(addrs))
        for addr in addrs:
            logger.debug(repr(addr))
            m = Message.make_outcoming(addr, msg, atts, **options)
            logger.debug(str(m.status))
            self.messages.append(m)
            if m.is_ready():
                logger.debug('pack ok, sending')
                engine.send_packet(m.packet)
            elif m.is_need_rsakey():
                logger.debug('need rsakey')
                self.req_pubkey(addr)
            elif m.is_encrypt_error():
                logger.debug('encryption error')
                pass
            else:
                logger.debug('Unknown status: %s' % m.status)
                pass

    def auto_reply(self, addr, msg=''):
        if not settings['enable_auto_reply'] or len(settings['auto_reply_msg']) == 0:
            return

        msg = Message.make_outcoming(addr, settings['auto_reply_msg'], [], autoret=True)
        if msg.is_ready():
            engine.send_packet(msg.packet)
        self.messages.append(msg)

    def proc_msg(self):
        self.events = set([])
        new_paused = engine.server.update()
        for msg in self.messages:
            for (p, addr) in new_paused:
                if msg.same_with(p):
                    msg.out_status = Message.PAUSED
        rslt = self.messages, self.events
        self.messages = [m for m in self.messages if not m.is_done()]
        return rslt

    # -------------- msg action ----------------

    def received(self, addr, msg=''):
        tag = c.IPMSG_RECVMSG
        engine.send(addr, tag, msg)

    def dispatch_msg(self, p):
        if p.dummy():
            return

        contact = engine.get_or_create_contact(p)
        for x in filter(p.is_type, self.command.keys()):
            def trace(f):
                @wraps(f)
                def inner(*args, **kws):
                    logger.debug('processing: %s' % (f.__name__))
                    f(*args, **kws)
                    logger.debug('processed: %s' % (f.__name__))
                return inner
            func = trace(self.command[x])
            func(p, contact)

    def rsps_entry(self, p, contact):
        if not status.is_invisible() and not status.is_off() and contact.addr[0] not in engine.block_ips:
            tag = c.IPMSG_ANSENTRY
            if status.is_afk():
                tag |= c.IPMSG_ABSENCEOPT
            msg = engine.get_name_ext()
            if engine.supports_utf8(p.addr) or settings['always_use_utf8']:
                tag |= c.IPMSG_UTF8OPT
            else:
                msg = util.utf8_to_sjis(msg)
            engine.send(contact.addr, tag, msg)
        if not engine.is_self(contact.addr):
            self.events.add(contact)
        self.req_pubkey(contact.addr)

    def rsps_ansentry(self, p, contact):
        if engine.is_self(contact.addr):
            return
        self.req_pubkey(contact.addr)

    def rsps_absence(self, p, contact):
        if p.test(c.IPMSG_ABSENCEOPT):
            contact.afk()
        else:
            contact.back()

    def rsps_exit(self, p, contact):
        contact.left()
        self.events.add(contact)

    def rsps_sendinfo(self, p, contact):
        contact.set_version(p.msg)
        engine.server.check_waiting(p, contact.addr, c.IPMSG_GETINFO)
        if engine.notify_callback is not None:
            engine.notify_callback(p.addr)

    def rsps_getinfo(self, p, contact):
        tag = c.IPMSG_SENDINFO
        msg = util.utf8_to_sjis(c.PROTOCOL_VERSION)
        engine.send(contact.addr, tag, msg)

    def rsps_sendabsenceinfo(self, p, contact):
        tag = c.IPMSG_GETABSENCEINFO
        engine.send(contact.addr, tag)

    def rsps_getabsenceinfo(self, p, contact):
        tag = c.IPMSG_SENDABSENCEINFO
        msg = self.auto_reply_msg
        engine.send(contact.addr, tag, msg)

    def rsps_recvmsg(self, p, contact):
        for msg in self.messages:
            if msg.same_with(p):
                msg.out_status = Message.SENT
        engine.server.check_waiting(p, contact.addr, c.IPMSG_SENDMSG)

    def rsps_ansreadmsg(self, p, contact):
        engine.server.check_waiting(p, contact.addr, c.IPMSG_READMSG)

    def find_message(self, packet):
        for msg in self.messages:
            if msg.io == 1 and msg.same_with(packet):
                return msg
        return None

    def rsps_sendmsg(self, p, contact):
        addr = contact.addr
        self.received(addr, p.cntr)
        if p.cntr <= contact.max_cntr:
            logger.debug('old message: %s <= %s' % (p.cntr, contact.max_cntr))
            return
        contact.max_cntr = p.cntr

        if self.find_message(p):
            logger.debug('already parsed')
            return

        msg = Message.parse_incoming(p, contact)
        logger.debug('msg ready')
        self.messages.append(msg)
        msg.write_log()
        if msg.is_decrypt_error():
            logger.debug('decryption error')
            self.received(addr, p.cntr)
            self.send([addr], c.DECRYPT_ERRMSG)
            return

        self.response_sendmsg(p, contact)

    def response_sendmsg(self, p, contact):
        addr = p.addr
        if not p.is_autoret():
            self.received(addr, p.cntr)
        if status.is_afk() and not p.is_autoret():
            self.auto_reply(addr)

    def rsps_getpubkey(self, p, contact):
        addr = contact.addr
        cry.memo(addr, capa=p.msg)
        tag = c.IPMSG_ANSPUBKEY
        msg = cry.get_pubkey_raw(addr)
        engine.send(addr, tag, msg)

    def rsps_anspubkey(self, p, contact):
        addr = contact.addr
        enc_capa, key = re.split(':', p.msg, 1)
        logger.debug('anspubkey: %s, %s, %s' % (repr(addr), enc_capa, key))
        cry.memo(addr, enc_capa, key)
        for msg in self.messages:
            if msg.io == 0 and msg.is_need_rsakey():
                msg.try_make_packet()
                if msg.is_ready():
                    engine.send_packet(msg.packet)

    def rsps_readmsg(self, p, contact):
        for msg in self.messages:
            if msg.io == 0 and msg.addr == p.addr and msg.get_cntr() == p.msg:
                msg.mark_open()
                if p.test(c.IPMSG_READCHECKOPT):
                    addr = p.addr
                    tag = c.IPMSG_ANSREADMSG
                    msg = p.cntr
                    engine.send(addr, tag, msg)
                return

    def rsps_delmsg(self, p, contact):
        for m in self.messages:
            if m.io == 0 and m.same_with(p):
                m.mark_ignore()

    # TODO: fill this
    def rsps_isgetlist(self, p, contact):
        pass

    def rsps_okgetlist(self, p, contact):
        pass

    def rsps_getlist(self, p, contact):
        pass

    def rsps_anslist(self, p, contact):
        engine.add_contact_list(p)

    def response_readmsg(self, p):
        addr = p.addr
        tag = c.IPMSG_READMSG | c.IPMSG_READCHECKOPT
        msg = p.cntr
        engine.send(addr, tag, msg)

    def req_pubkey(self, addr):
        tag = c.IPMSG_GETPUBKEY
        msg = shex(cry.encrypt_capa)
        engine.send(addr, tag, msg)

    def open_notice(self, msg):
        for m in self.messages:
            if m == msg:
                m.mark_open()
                tag = c.IPMSG_READMSG
                engine.send(m.addr, tag, m.get_cntr())

    def read_notice(self, msg):
        for m in self.messages:
            if m == msg:
                m.mark_read()

    def delete_notice(self, msg):
        for m in self.messages:
            if m == msg:
                m.mark_ignore()
                tag = c.IPMSG_DELMSG
                engine.send(m.addr, tag, m.get_cntr())

    def resend(self, msg):
        msg.reset_to_sending()
        engine.server.resend((msg.packet, msg.addr))

