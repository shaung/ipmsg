# -*- coding: utf-8 -*-

import re, time, logging

import consts as c
from contact import Contact

log = logging.getLogger('Packet')

class Packet:
    @classmethod
    def parse(cls, raw, addr=()):
        self = cls()
        self.timestamp = time.time()
        self.raw = raw
        self.raw_msg = ''
        self.atts = []
        self.addr = addr
        self.unpack(raw)
        return self

    def age(self):
        age = time.time() - self.timestamp
        return age > 0 and age or 0

    def values(self):
        return [self.ver, self.cntr, self.name, self.host, self.tag, self.msg, self.ext]

    def __eq__(self, other):
        return self.cntr == other.cntr and self.tag == other.tag

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return long(str(int(self.timestamp)) + str(self.cntr) + str(self.tag))

    def unpack(self, raw):
        log.debug('unpacking....' + raw)

        msgstr = ''
        self.ver, self.cntr, self.name, self.host, self.tag, msgstr = re.split(':', raw, 5)
        msgstr = re.sub('\0+', '\0', msgstr)
        data = list(re.split('\0', msgstr))

        self.msg, self.ext = map(''.join, (data[:1], data[1:]))
        self.raw_msg = self.msg
        # since v3 there is extended utf8 trailer for broadcast packets.
        # that trailer is ensured to be utf8 so we need to ignore it when converting to unicode
        if self.is_br() or self.is_nop():
            uinfo = {
                'UN': self.name,
                'HN': self.host,
                'NN': self.to_unicode(self.msg),
                'GN': '',
            }
            try:
                uinfo['GN'], utf8ext = re.split('\n', self.ext, 1)
            except ValueError:
                log.debug('extra trailer not found')
                self.ext, self.name = self.to_unicode(self.ext, self.name)
                uinfo['GN'] = self.ext
            else:
                self.ext = self.to_unicode(uinfo['GN'])
                log.debug('extra trailer: %s' % utf8ext)
                for entry in utf8ext.split('\n'):
                    tag, name = entry.split(':')
                    log.debug(' %s: %s' % (tag, name))
                    if tag in uinfo:
                        uinfo[tag] = name
            self.name = uinfo.get('UN')
            self.host = uinfo.get('HN')
            self.msg  = uinfo.get('NN')
            self.group = uinfo.get('GN')
        else:
            if not (self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_ENCRYPTOPT)):
                self.msg = self.to_unicode(self.msg)
            self.group = self.ext = self.to_unicode(self.ext)
            self.name = self.to_unicode(self.name)

        self.group = self.group.replace('\n', '')

        if self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_FILEATTACHOPT):
            self.atts = [Attachment(x, self.cntr) for x in re.split('\x07', self.ext) if x]

        log.debug('msg=' + self.msg)
        log.debug('ext=' + self.ext)

    def extract_contact(self):
        if not self.type_in(c.IPMSG_BR_ENTRY, c.IPMSG_ANSENTRY):
            contact = Contact(name=self.name, group='', host=self.host, addr=self.addr, login=self.name)
            contact.temporary = True
        else:
            contact = Contact(name=self.msg, group=self.group, host=self.host, addr=self.addr, login=self.name)
            contact.encrypt_opt = self.test(c.IPMSG_ENCRYPTOPT)
        return contact

    def extract_contact_list(self):
        rslt = []
        if not self.type_in(c.IPMSG_ANSLIST):
            return []
        g_cnt, c_cnt, bunch = re.split('\x07', self.raw_msg, 2)
        raw_list = re.split('\x07', bunch)[:-1]
        while raw_list:
            raw = raw_list[:7]
            raw_list = raw_list[7:]
            tag = raw[2]
            addr = list(self.addr)
            addr[0] = raw[3]
            wtf = raw[4]
            name = self.to_unicode(raw[5])
            login = self.to_unicode(raw[0])
            group = self.to_unicode(raw[6])
            contact = Contact(name=name, group=group, host=raw[1], addr=tuple(addr), login=login)
            contact.encrypt_opt = (int(tag) & c.IPMSG_ENCRYPTOPT)
            rslt.append(contact)
        return rslt

    def to_unicode(self, *args):
        sjisdecode = lambda x : x.decode('cp932', 'replace')
        utf8decode = lambda x : x.decode('utf-8', 'replace')
        rslt = map(self.test(c.IPMSG_UTF8OPT) and utf8decode or sjisdecode, (args))
        if len(rslt) == 1:
            return rslt[0]
        else:
            return rslt

    def has_all(self, *flags):
        return len([x for x in flags if not self.test(x)]) == 0

    def has_any(self, *flags):
        return len([x for x in flags if self.test(x)]) > 0

    def test(self, flag):
        return (int(self.tag) & flag) == flag

    def is_type(self, flag):
        return (int(self.tag) & 0xFF) == flag

    def type_in(self, *flags):
        return len([x for x in flags if self.is_type(x)]) == 1

    def dummy(self):
        return self.tag in ('0', '')

    def is_nop(self):
        return self.is_type(c.IPMSG_NOOPERATION)

    def has_check_option(self):
        return (self.is_type(c.IPMSG_SENDMSG) and
                self.test(c.IPMSG_SENDCHECKOPT) and
                not self.is_broadcast() and
                not self.is_autoret()
               ) or \
               (self.is_type(c.IPMSG_READMSG) and self.test(c.IPMSG_READCHECKOPT))

    def is_br(self):
        return self.type_in(c.IPMSG_BR_ENTRY, c.IPMSG_BR_EXIT, c.IPMSG_BR_ABSENCE)

    def is_status_notify(self):
        return self.type_in(c.IPMSG_BR_ENTRY, c.IPMSG_ANSENTRY, c.IPMSG_BR_ABSENCE)

    def is_absence(self):
        return self.is_status_notify() and self.test(c.IPMSG_ABSENCEOPT)

    def is_encrypted(self):
        return self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_ENCRYPTOPT)

    def needs_readcheck(self):
        return self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_READCHECKOPT)

    def is_autoret(self):
        return self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_AUTORETOPT)

    def is_multicast(self):
        return self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_MULTICASTOPT)

    def is_broadcast(self):
        return self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_BROADCASTOPT)

    def is_secret(self):
        return self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_SECRETOPT)

    def is_with_password(self):
        return self.is_secret() and self.test(c.IPMSG_PASSWORDOPT)

    def is_utf8(self):
        return self.is_type(c.IPMSG_SENDMSG) and self.test(c.IPMSG_UTF8OPT)

class Attachment:
    def __init__(self, att, cntr):
        self.id = 0x0
        self.name = ""
        self.size = 0x0
        self.mtime = 0x0
        self.attr = 0x0
        self.ext = []
        self.cntr = cntr

        if len(att) > 0:
            self.unpack(att)

    def unpack(self, att):
        att = att.replace('::', ':')
        li = re.split(":", att, 5)
        self.id, self.name, self.size, self.mtime, self.attr = li[:5]
        self.ext = li[5:]

    def values(self):
        return [self.id, self.name, self.size, self.mtime, self.attr, self.ext, self.cntr]


