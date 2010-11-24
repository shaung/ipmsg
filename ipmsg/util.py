# -*- coding: utf-8 -*-

import sys, os, re, binascii, stat

__all__ = ['shex', 'utf8_to_explode', 'utf8_to_uni', 'sjis_to_uni']

def shex(num):
    return hex(num)[2:type(num) == long and -1 or None]

def utf8_to_explode(s):
    rslt = ''
    us = unicode(s, 'utf-8', 'replace')
    for x in us:
        raw_x = x.encode('utf-8', 'replace')
        bx = raw_x + '\xd2\x89'
        if binascii.b2a_hex(raw_x) < 128:
            bx += '\xd2\x89'
        rslt += bx

    return rslt

def utf8_to_uni(utf8):
    return utf8.decode('utf-8', 'replace')

def sjis_to_uni(sjis):
    return sjis.decode('cp932', 'replace')

def uni_to_utf8(uni):
    return uni.encode('utf-8', 'replace')

def uni_to_sjis(uni):
    return uni.encode('cp932', 'replace')

def sjis_to_utf8(sjis):
    return unicode(sjis, 'cp932', 'replace').encode('utf-8', 'replace')

def utf8_to_sjis(utf8):
    return unicode(utf8, 'utf-8', 'replace').encode('cp932', 'replace')

class AttachmentError(Exception):
    def __init__(self, msg=''):
        self.msg = msg

    def __str__(self):
        return self.msg

def verify_files(*files):
    for f in files:
        if not os.path.exists(f):
            raise AttachmentError, 'file not exist'
        fstat = os.stat(f)
        fuid, fgid = fstat[stat.ST_UID], fstat[stat.ST_GID]
        if fuid == 0 or fgid == 0:
            raise AttachmentError, 'owner is root'
        myuid, mygid = os.getuid(), os.getgid()
        if fuid != myuid or fgid != mygid:
            if not fstat[stat.S_IROTH]:
                raise AttachmentError, 'no read permission'
    return True

def verify_dir(save_dir):
    if not save_dir:
        save_dir = os.path.join('download', str(time.time()))

    if not os.path.exists(save_dir):
        try:
            os.mkdir(save_dir)
        except:
            return False

    return True

def cloudy(msg, encoding):
    ext_msg = msg
    if encoding == 'utf-8':
        ext_msg = utf8_to_explode(msg)
    return ext_msg

def get_nic_list(default_nic=None):
    def get_ip(interface):
        f = os.popen("ifconfig %s | grep inet | awk '{print $2}' | sed -e s/.*://" % interface, "r")
        ip = f.readline().strip()
        return interface, ip
    li = map(get_ip, default_nic or filter((lambda x : x != 'lo'), os.popen("ifconfig -s | awk '{print $1}'").read().strip().split('\n')[1:]))
    return filter((lambda (n, ip) : len(ip) > 0), li)

def expand_ip(ip):
    li = ip.split('.')
    assert(len(li) == 4)

    def normalize(li):
        rslt = []
        for x in li[0]:
            if len(li) == 1:
                rslt.append(x)
            else:
                suffix = normalize(li[1:])
                rslt += (['.'.join([str(m) for m in n]) for n in zip(len(suffix) * [x], suffix)])
        return rslt

    rslt = []
    for n in li:
        if n == '*':
            start, end = 1, 255
        elif '-' in n:
            start, end = n.split('-')
            start = start and int(start) or 1
            end = end and int(end) + 1 or 255
        else:
            start, end = int(n), int(n) + 1
        rslt.append(range(start, end))
    return normalize(rslt)

def verify_ip(item):
    """
        determine if the input is ip address/mask
    """

    if len(item) < 7:
        return False
    if len(re.findall(r'[^0-9*-.]+', item)) > 0:
        return False

    try:
        li = item.split('.')
        if len(li) != 4:
            return False
        for x in [x for x in li if x != '*']:
            if len(x) == 0:
                return False
            li = '-' in x and x.split('-') or [x]
            if len([x for x in li if x != '' and (int(x) < 0 or int(x) > 255)]) > 0:
                return False
    except:
        return False
    return True

