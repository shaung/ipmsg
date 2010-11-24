# -*- coding: utf-8 -*-

import gtk
import os, sys, subprocess, stat, re

def calc_time(age):
    t = int(age)
    rslt = ''
    if t < 0:
        return rslt
    for i, v in ((60, 'm'), (60, 'h'), (24, 'd')):
        t /= i
        if t == 0 and rslt:
            break
        rslt = str(t%i) + v + rslt
    return rslt

def normalize_size(size):
    sz = float(size)
    for i, v in [(0, 'b'), (1, 'kb'), (2, 'mb'), (3, 'gb')]:
        if size < pow(1024, i+1):
            return '%.2f%s' % (sz / pow(1024, i), v)
    return str(size) + 'b'

def launch_file(fpath):
    if sys.platform == 'linux2':
        subprocess.call(['xdg-open', fpath])
    else:
        os.startfile(fpath)

ESCAPE_MAP = {
    '<': '&lt;',
    '>': '&gt;',
    "'": '&apos;',
    '"': '&quot;',
    '&': '&amp;',
}

def escape_markup(text):
    rslt = text
    for ori, rep in ESCAPE_MAP.items():
        rslt = re.sub(ori, rep, rslt)
    return rslt

def unescape_markup(text):
    rslt = text
    for ori, rep in ESCAPE_MAP.items():
        rslt = re.sub(rep, ori, rslt)
    return rslt


def get_keyvals(keystr):
    mod_map = {
        'Control': gtk.gdk.CONTROL_MASK,
        'Alt': gtk.gdk.MOD1_MASK,
        'Shift': gtk.gdk.SHIFT_MASK,
    }

    keynames = keystr.split('+')
    if not keynames:
        return None

    masks = []
    keyval = gtk.gdk.keyval_from_name(keynames[-1])
    if len(keynames) > 1:
        masks = [mod_map[x] for x in keynames[:-1]]

    return masks, keyval

