# -*- coding: utf-8 -*-

import re, time, logging

import consts as c

log = logging.getLogger('Parts')

class Contact:
    def __init__(self, name, group, host, addr, login=''):
        self.name = name
        self.group = group
        self.host = host
        self.login = login
        self.addr = addr #(ip, port)
        self.version = ''
        self.status = c.STAT_ON
        self.encrypt_capa = 0
        self.key = {}
        self.max_cntr = 0
        self.encrypt_opt = None
        self.timestamp_on = time.time()
        self.timestamp_left = 0
        self.temporary = False

    def age(self):
        age = time.time() - self.timestamp_on
        return age > 0 and age or 0

    def has_left_for(self):
        if self.timestamp_left == 0:
            return -1
        secs = time.time() - self.timestamp_left
        return secs > 0 and secs or 0

    def left(self):
        self.status = c.STAT_OFF
        self.version = ''
        self.timestamp_left = time.time()

    def afk(self):
        self.status = c.STAT_AFK
        self.timestamp_left = 0

    def back(self):
        self.status = c.STAT_ON
        self.timestamp_left = 0

    def set_version(self, ver):
        self.version = ver

    def supports_utf8(self):
        if len(self.version) == 0:
            return False
        else:
            m = re.match(u'Win32版 Ver(.*)', self.version)
            if m:
                try:
                    main, minor = m.group(1).split('.')
                    if int(main) < 2 or int(minor) <= 6:
                        return False
                except:
                    pass
            return True

    def get_desc(self):
        if len(self.group) == 0:
            return self.name
        else:
            return '%s(%s)' % (self.name, self.group)

    def get_id(self):
        return ':'.join(map(str, self.addr))


