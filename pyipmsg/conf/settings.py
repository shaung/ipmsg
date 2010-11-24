# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk, gobject, gnome, gnomeapplet, gconf
import sys, os, os.path, subprocess, time, copy
import urllib, re
import logging, logging.config

from pyipmsg.icons import *

class GConfCategory:
    def __init__(self, key):
        self.__key = key
        self.__client = gconf.client_get_default()
        self.__dir = '/apps/pyipmsg'
        if not self.__client.dir_exists(self.__dir):
            self.__client.add_dir(self.__dir, gconf.CLIENT_PRELOAD_NONE)

    def __gen_key(self, name):
        return '%s/%s/%s' % (self.__dir, self.__key, name)

    def set(self, name, val):
        key = self.__gen_key(name)
        value = val
        self.__client.set_value(key, value)

    def get(self, name):
        key = self.__gen_key(name)
        return self.__client.get_value(key)

class GConfProperty(GConfCategory):
    def __init__(self, path, key, default):
        GConfCategory.__init__(self, key=path)
        self.__name = key
        self.__default = default

    def set(self, val):
        GConfCategory.set(self, self.__name, val)

    def get(self):
        try:
            return GConfCategory.get(self, self.__name)
        except ValueError:
            self.set(self.__default)
            return self.__default

    def notify_add(self, notify_cb):
        self.__client.notify_add(self.__gen_key(self.__name), notify_cb)

class SettingsDialog:
    def __init__(self, key, parent=None):
        self.parent = parent
        dlg = gtk.Dialog('Settings', parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        dlg.set_size_request(500, 300)
        dlg.action_area.set_homogeneous(False)
        dlg.action_area.set_spacing(10)

        btn_revert = gtk.Button(label='Revert')
        btn_revert.show()
        btn_revert.set_has_tooltip(True)
        btn_revert.set_tooltip_markup('Revert the changes')
        btn_revert.connect("button_press_event", self.do_revert)
        dlg.action_area.pack_end(btn_revert, False, False, 0)

        btn_close = gtk.Button(label='Close')
        btn_close.show()
        btn_close.connect("button_press_event", self.do_close)
        dlg.action_area.pack_end(btn_close, False, False, 0)

        self.dlg = dlg

        self._build()

    def _build(self):
        panel = gtk.Frame()
        panel.show()

        self.win = gtk.ScrolledWindow()
        self.win.show()
        self.win.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        panel.set_border_width(0)
        self.vbox = gtk.VBox()
        self.vbox.show()
        panel.add(self.vbox)
        self.vbox.set_spacing(10)
        self.win.add_with_viewport(panel)
        self.dlg.vbox.pack_start(self.win)

        self.preserve()

    def preserve(self):
        self.props = {}
        for key in self.parent.get_all_properties():
            self.props[key] = self.parent.get_gconf(key)

    def add_page(self, name, controls):
        if len(name) > 0:
            item = gtk.MenuItem(name)
            item.select()
            item.show()
            self.vbox.pack_start(item, False, False)
 
        tbl = gtk.Table(2, len(controls))
        tbl.show()
        tbl.set_row_spacings(5)
        tbl.set_col_spacings(5)

        for idx, (ctl_name, ctl) in enumerate(controls):
            lbl = gtk.Label(ctl_name)
            lbl.set_justify(gtk.JUSTIFY_LEFT)
            lbl.show()
            hbox = gtk.HBox(False, 6)
            hbox.show()
            hbox.pack_start(lbl, False, False)
            tbl.attach(hbox, 0, 1, idx, idx + 1, gtk.FILL)
            hbox = gtk.HBox(False, 6)
            hbox.show()
            hbox.pack_start(ctl, True, True)
            vbox = gtk.VBox()
            vbox.show()
            vbox.pack_start(hbox, False, False)
            tbl.attach(vbox, 1, 2, idx, idx + 1, gtk.FILL | gtk.EXPAND)
        self.vbox.pack_start(tbl, False, False, 5)

    def do_revert(self, widget, event, *args):
        self.restore()
        self.dlg.vbox.remove(self.win) 
        self._build()

    def do_close(self, widget, event, *args):
        self.dlg.destroy()

    def restore(self):
        for k, v in self.props.items():
            self.parent.set_gconf(k, v)
        self.parent.update_gconf()

    def run(self):
        self.dlg.show()
        self.dlg.run()
        self.dlg.destroy()

