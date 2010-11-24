# -*- coding: utf-8 -*-

import time, re
from datetime import datetime

class Logger:
    def __init__(self, fpath):
        self.bind(fpath)

    def bind(self, fpath):
        self.fpath = fpath

    def log_send(self, *args):
        self._log(0, *args)

    def log_recv(self, *args):
        self._log(1, *args)

    def _log(self, io, contact, msg, attach):
        log = MessageLog(io, contact, msg, attach, '')
        self._write_to_log(log.content)

    def _write_to_log(self, lines):
        f = file(self.fpath, 'a')
        f.write(lines)
        f.flush()
        f.close()

class MessageLog:
    content = ''
    io = 0
    contact_name = ''
    contact_group = ''
    contact_host = ''
    contact_addr = ''
    time = ''
    attachments = []
    enc_method = ''
    msg = ''

    def __init__(self, io=0, contact=None, msg='', attachments=[], enc_method=''):
        self.time = time.time()
        self.io = io
        if contact:
            self.contact_name = contact.name
            self.contact_group = contact.group
            self.contact_host = contact.host
            self.contact_addr = contact.addr[0]
        self.msg = msg
        self.attachments = attachments
        self.enc_method = enc_method
        self.content = self.to_string()

    def values(self):
        return [self.io, self.contact_name, self.contact_group, self.contact_host, self.contact_addr, \
                self.time_str, self.time, self.attachments, self.enc_method, self.msg,]

    def to_string(self):
        lines = []
        lines.append('='*38)
        identify_str = '/'.join([self.contact_host, self.contact_addr])
        if self.contact_group:
            identify_str = self.contact_group + '/' + identify_str
        lines.append(' %s: %s (%s)' % (self.io and 'From' or 'To', self.contact_name, identify_str))
        lines.append('  at %s %s' % (str(time.ctime(self.time)), self.enc_method))
        if self.attachments:
            lines.append('  (Yt) %s' % ', '.join(self.attachments))
        lines.append('-'*38)
        lines.append(self.msg)
        lines.append('')
        lines.append('')
        return '\n'.join(lines)

    @classmethod
    def parse(cls, content):
        self = cls()
        self.content = content
        lines = self.content.split('\n')
        m_contact = re.match(r"""
            ^\ *(From|To):\ *          #direction
            ([^\(]*)                   #name
            \(([^\)]*).*               #group/host/addr
            """, lines[0], re.X)
        if m_contact.group(1) == 'From':
            self.io = 1
        elif m_contact.group(1) == 'To':
            self.io = 0
        else:
            pass 
        self.contact_name = m_contact.group(2)
        addr_li = re.split('/', m_contact.group(3), 3)[::-1]
        while len(addr_li) < 3:
            addr_li.append('')
        self.contact_addr, self.contact_host, self.contact_group = addr_li
        lines = lines[1:]
        
        if lines[0][-1] == ')':
            m_time = re.match('^  at ([^\(]*)\(([^\(]*)) ', lines[0])
        else:
            m_time = re.match('^  at (.*)', lines[0])
        self.time_str = m_time.group(1).rstrip()
        self.time = datetime.strptime(self.time_str, '%a %b %d %H:%M:%S %Y')
        try:
            self.enc_method = m_time.group(2)
        except IndexError:
            pass
        lines = lines[1:]

        if len(lines[0]) > 0 and lines[0][0] != '-':
            m_attach = re.match('^ *\(Yt\) *(.*)', lines[0])
            self.attachments = re.split(',', m_attach.group(1))
            lines = lines[1:]

        lines = lines[1:]

        self.msg = '\n'.join(lines)

        return self


