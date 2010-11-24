# -*- coding: utf-8 -*-

from ipmsg.config import settings

category_message = [
    ('default_seal_msg', False),
    ('default_webshare', False),
    ('default_quote_msg', False),
    ('keep_recv_window_when_reply', False),
    ('enable_popup', False),
    ('non_popup_when_afk', False),
    ('enable_notify', False),
    ('disable_notify_afk', False),
    ('notify_online', False),
    ('notify_offline', False),
    ('notify_error', False),
]
 
settings.add_fields('message', *category_message)

category_hotkey = [
    ('hotkey_send', 'Alt+s'),
    ('hotkey_reply', 'Alt+r'),
]

settings.add_fields('hotkey', *category_hotkey)

category_other = [
    ('grouping', False),
] 

settings.add_fields('other', *category_other)
