# -*- coding: utf-8 -*-

import logging

from ipmsg import consts as c
from ipmsg.config import settings
from ipmsg.packet import Packet
from ipmsg.contact import Contact
from ipmsg.crypto import cry
from ipmsg import util
from ipmsg.share import upload_manager, webshare_manager
from ipmsg.status import status
from ipmsg.history import Logger as MessageLogger

from engine import engine

message_logger = MessageLogger(settings['log_file_path'])

logger = logging.getLogger(__file__)

"""
    Message class.
    Takes care of encoding / encryption / decryption / packet pack/unpack
"""
class Message:
    NEED_RSAKEY, ENCRYPT_ERROR, ENCRYTED, DECRYPT_ERROR, INIT, READ, OPENED, IGNORED = range(8)
    SENDING, SENT, PAUSED = range(3)

    packet = None
    contact = None
    io = 0
    addr = None
    status = INIT
    out_status = SENDING

    timestamp = None
    cntr = 0
    msg = ''
    atts = []

    options = {
        'autoret': False,
        'multicast': False,
        'encrypt': True,
        'read_check': False,
        'seal': False,
        'password': False,
        'webshare': False,
    }

    @classmethod
    def make_outcoming(cls, addr, msg, atts, **options):
        self = cls()
        self.io = 0
        self.msg = msg
        self.addr = addr
        self.atts = atts
        self.options = cls.options.copy()
        self.options.update(**options)
        if self.options['seal'] and settings['do_readmsg_chk']:
            self.options['read_check'] = True
 
        if self.options['encrypt']:
            self.status = Message.NEED_RSAKEY
        logger.debug('get_contact')
        self.contact = engine.get_contact(self.addr)
        self.try_make_packet()

        if self.options['autoret']:
            self.out_status = Message.SENT

        return self

    def try_make_packet(self):
        logger.debug('try_make_packet')
        tag = 0
        tag |= c.IPMSG_SENDMSG
        tag |= c.IPMSG_SENDCHECKOPT
        tag |= c.IPMSG_RETRYOPT

        if status.is_invisible() or self.addr[0] in settings['block_list']:
            tag |= c.IPMSG_NOADDLISTOPT
        elif status.is_afk():
            tag |= c.IPMSG_ABSENCEOPT

        if self.options['autoret']:
            tag |= c.IPMSG_AUTORETOPT

        if self.options['seal']:
            tag |= c.IPMSG_SECRETOPT
            if self.options['read_check']:
                tag |= c.IPMSG_READCHECKOPT
            if self.options['password']:
                tag |= c.IPMSG_PASSWORDOPT

        if engine.supports_utf8(self.addr):
            tag |= c.IPMSG_UTF8OPT
            encode_func = util.uni_to_utf8
        else:
            encode_func = util.uni_to_sjis

        msg = self.msg

        if self.atts and self.options['webshare']:
            msg += '\n\n' + webshare_manager.start(self.atts)

        contact = engine.get_contact(self.addr) or Contact(name='', group='', host='', addr=self.addr)

        msg = unicode(msg, 'utf8')
        msg = encode_func(msg)

        if self.options['encrypt']:
            rslt = self.encrypt(msg, contact)
            if not rslt:
                logger.debug('encrypt failed')
                return
            else:
                logger.debug('encrypt success')
                is_enc, msg = rslt
                if is_enc:
                    tag |= c.IPMSG_ENCRYPTOPT

        if self.atts and not self.options['webshare']:
            tag |= c.IPMSG_FILEATTACHOPT
            msg += '\x00' + encode_func(upload_manager.append_files(self.addr, self.atts))

        logger.debug('ready to make msg')
        raw = engine.make_msg(self.addr, tag, msg)
        self.packet = Packet.parse(raw, self.addr) 
        self.status = Message.INIT

        self.write_log()

    def encrypt(self, msg, contact=None):
        logger.debug('ready to encrypt')
        if not contact or not cry.knows(self.addr):
            self.status = Message.NEED_RSAKEY
            # no knowledge about this contact, ask for capa and key
            logger.debug('unknown contact')
            return None
        elif not contact.encrypt_opt or not cry.understands(self.addr):
            self.status = Message.INIT
            logger.debug('contact does not support the encryption method')
            return False, self.msg

        logger.debug('before calling encryption')
        rslt, enc_msg = cry.encrypt(msg, self.addr)
        if rslt:
            logger.debug('encryption success')
            self.status = Message.INIT
            return True, enc_msg
        else:
            logger.debug('encryption error')
            self.status = Message.ENCRYPT_ERROR
            return None

    @classmethod
    def parse_incoming(cls, packet, contact):
        logger.debug('try parse incoming')
        self = cls()
        self.io = 1
        self.timestamp   = packet.timestamp
        self.cntr        = packet.cntr
        self.addr        = packet.addr
        self.msg         = packet.msg
        self.atts        = packet.atts
        self.options = cls.options.copy()
        self.options['multicast']   = packet.is_multicast()
        self.options['encrypt']     = packet.is_encrypted()
        self.options['read_check']  = packet.needs_readcheck()
        self.options['autoret']     = packet.is_autoret()
        self.options['seal']        = packet.is_secret()
        self.options['password']    = packet.is_with_password()
 
        self.packet = packet
        self.contact = contact

        if self.options['encrypt']:
            self.status = Message.ENCRYTED
            self.decrypt()
        else:
            self.status = Message.INIT
        return self

    def decrypt(self):
        rslt, dec_msg = cry.decrypt(self.msg)
        if not rslt:
            self.status = DECRYPT_ERROR
            return

        encode_func = self.packet.is_utf8() and util.utf8_to_uni or util.sjis_to_uni
        self.msg = encode_func(dec_msg)
        self.status = Message.INIT

    def same_with(self, packet):
        return self.get_cntr() == packet.cntr and self.addr == packet.addr

    def reset_to_sending(self):
        self.out_status = Message.SENDING

    def is_send_error(self):
        return self.out_status == Message.PAUSED

    def is_decrypt_error(self):
        return self.status == Message.DECRYPT_ERROR

    def is_ready(self):
        return self.status == Message.INIT

    def is_encrypt_error(self):
        return self.status == Message.ENCRYPT_ERROR

    def is_need_rsakey(self):
        return self.status == Message.NEED_RSAKEY

    def is_done(self):
        if self.options['read_check']:
            return self.is_opened() or self.is_ignored()
        elif self.io == 1:
            return self.is_read()
        elif self.io == 0:
            return False

    def is_sent(self):
        return self.io == 0 and self.out_status == Message.SENT

    def is_read(self):
        return self.status == Message.READ

    def is_opened(self):
        return self.status == Message.OPENED

    def is_ignored(self):
        return self.status == Message.IGNORED

    def get_message(self):
        return self.msg

    def get_attachments(self):
        return self.atts

    def get_contact(self):
        return self.contact

    def get_addr(self):
        return self.addr

    def get_cntr(self):
        return self.packet and self.packet.cntr or self.cntr

    def mark_read(self):
        self.status = Message.READ

    def mark_open(self):
        self.status = Message.OPENED

    def mark_ignore(self):
        self.status = Message.IGNORED

    def write_log(self):
        log_func = self.io and message_logger.log_recv or message_logger.log_send
        if settings['enable_log']:
            log_func(self.get_contact() or engine.get_contact(self.addr), self.msg, self.io and [att.name for att in self.atts] or self.atts)

class Event:
    CONTACT_ONLINE, CONTACT_OFFLINE = range(2)
    type = None
    contact = None

    def __init__(self, type, contact):
        self.type = type
