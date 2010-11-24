# -*- coding: utf-8 -*-

import os, time, logging
import pynotify

from pyipmsg import icons

logger = logging.getLogger('Notify')

if not pynotify.init("pymsg notification"):
    logger.debug('pynotify init failed')

SYSTEM, EVENT, MSG, ATT = range(4)

NOTIFY_ICONS = {
    SYSTEM   : "system",
    EVENT    : "event",
    MSG      : "message",
    ATT      : "attachment",
}

_notify = None
_title = ''
_text = ''
_timestamp = time.time()

def balloon(title='', text='', icon_type=MSG, expires=pynotify.EXPIRES_DEFAULT):
    global _notify, _title, _text, _timestamp
    assert(icon_type in NOTIFY_ICONS)
    utitle = title.encode('utf-8', 'replace')
    utext = text.encode('utf-8', 'replace')

    icon_path = icons.Notify.get_path(NOTIFY_ICONS[icon_type]) 
    if _notify == None:
        _notify = pynotify.Notification(utitle, utext, icon_path)
    else:
        if _title == utitle and time.time() - _timestamp < 10:
            utext = _text + '\n\n' + utext
            _notify.update(utitle, utext, icon_path)
        else:
            _notify = pynotify.Notification(utitle, utext, icon_path)

    _timestamp = time.time()
    _title, _text = utitle, utext

    _notify.set_timeout(expires)
    if not _notify.show():
        logger.debug('failed sending notification')
 
def clean():
    pynotify.uninit()

if __name__ == "__main__":
    balloon('test1', 'this is an event notification', EVENT, 1)
    balloon('test1', 'again an event notification', EVENT, 1)
    balloon('test3', 'followed by a new att notification', ATT, 2)
    balloon('test2', 'followed by a new msg notification', MSG, 4)
    balloon('test2', 'and followed by another new msg notification', MSG, 2)
    clean()

