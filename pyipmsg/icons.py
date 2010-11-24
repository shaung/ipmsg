# -*- coding: utf-8 -*-

import os.path
import gtk
from ipmsg.status import *
from pyipmsg.common import INSTALL_ROOT_DIR

resdir = os.path.join(INSTALL_ROOT_DIR, 'icons')

class IconBase:
    _default_icon = os.path.join(resdir, 'missing.png')

    _STATUS = {
        STAT_ON        : "status-on",
        STAT_AFK       : "status-afk",
        STAT_INVISIBLE : "status-invisible",
        STAT_OFF       : "status-off",
    }

    _image_buf = {}

    @classmethod
    def _get(cls, name):
        return os.path.join(cls._root_dir, cls._ICONS[name])

    @classmethod
    def get_path(cls, name):
        try:
            fpath = cls._get(name)
            assert(os.path.exists(fpath))
        except:
            fpath = cls._default_icon
        return fpath

    @classmethod
    def _get_or_create_image(cls, name):
        key = cls.__name__ + name
        if key not in cls._image_buf:
            img = gtk.Image()
            img.set_from_file(cls.get_path(name))
            cls._image_buf[key] = img
        return cls._image_buf[key]

    @classmethod
    def _get_pixbuf(cls, name):
        image = cls._get_or_create_image(name)
        return image.get_pixbuf()

    @classmethod
    def get_image(cls, name, cache=True):
        image = cls._get_or_create_image(name)
        return cache and image or gtk.image_new_from_pixbuf(image.get_pixbuf())

    @classmethod
    def get_pixbuf(cls, name, cache=True):
        pixbuf = cls._get_pixbuf(name)
        return cache and pixbuf or pixbuf.copy()

    @classmethod
    def get_status_path(cls, status_id):
        return cls.get_path(cls._STATUS[status_id])

    @classmethod
    def get_status_image(cls, status_id, cache=True):
        return cls.get_image(cls._STATUS[status_id], cache)

    @classmethod
    def get_status_pixbuf(cls, status_id, cache=True):
        return cls.get_pixbuf(cls._STATUS[status_id], cache)

class Toolbar(IconBase):
    _root_dir = os.path.join(resdir, 'toolbar')

    _ICONS = {
        'search'            : 'search.png',
        'attachment'        : 'attachment.png',
        'group-on'          : 'group-on.png',
        'group-off'         : 'group-off.png',
        'refresh'           : 'refresh.png',
        'settings'          : 'settings.png',
        'settings-hover'    : 'settings-hover.png',
        'save-layout'       : 'save-layout.png',
        'save-layout-hover' : 'save-layout-hover.png',
    }

class Menu(IconBase):
    _root_dir = os.path.join(resdir, 'menu')

    _ICONS = {
        'status-on'         : 'status-on.png',
        'status-afk'        : 'status-afk.png',
        'status-invisible'  : 'status-invisible.png',
        'status-off'        : 'status-off.png',
        'block'             : 'block.png',
    }

class Window(IconBase):
    _root_dir = os.path.join(resdir, 'window')

    _ICONS = {
        'msg-normal'        : 'msg-normal.png',
        'msg-autoreply'     : 'msg-autoreply.png',
        'msg-multicast'     : 'msg-multicast.png',
    }

class App(IconBase):
    _root_dir = os.path.join(resdir, 'app')

    _ICONS = {
        'logo'              : 'logo.png',
        'status-on'         : 'status-on.png',
        'status-afk'        : 'status-afk.png',
        'status-invisible'  : 'status-invisible.png',
        'status-off'        : 'status-off.png',
        'normal'            : 'normal.png',
        'message'           : 'message.png',
        'attachment'        : 'attachment.png',
    }

class Notify(IconBase):
    _root_dir = os.path.join(resdir, 'notify')

    _ICONS = {
        'system'        : 'system.png',
        'event'         : 'event.png',
        'message'       : 'message.png',
        'attachment'    : 'attachment.png',
    }

class Misc(IconBase):
    _root_dir = os.path.join(resdir, 'misc')

    _ICONS = {}

