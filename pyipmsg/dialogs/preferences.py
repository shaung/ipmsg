# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk, gobject, glib, pango
import sys, os, os.path, copy
import urllib, re, string
import logging

import ipmsg
from ipmsg.status import *
from ipmsg import config
from ipmsg.config import settings, categories

from pyipmsg.widgets import MultiEntry, CellRendererImageButton
from pyipmsg import icons
from pyipmsg.dialogs.configable import ConfigableDialog
from pyipmsg.conf.settings import GConfProperty
from pyipmsg import util

class StatusBox(gtk.ComboBoxEntry):
    def __init__(self):
        ls = gtk.ListStore(int, str, str, bool, bool)
        ls.set_sort_column_id(0, gtk.SORT_ASCENDING)
        gtk.ComboBoxEntry.__init__(self, ls, 1)
        self.clear()

        self.current_status = STAT_OFF

        self.connect('changed', self.changed_cb)

        icon = gtk.CellRendererPixbuf()
        self.pack_start(icon, False)
        def icon_data_func(layout, cell, model, itr, userdata):
            cell.set_property('pixbuf', icons.Menu.get_status_pixbuf(model.get_value(itr, 0)))
        self.set_cell_data_func(icon, icon_data_func, None)
        txt = gtk.CellRendererText()
        txt.ellipsize = pango.ELLIPSIZE_END
        self.pack_start(txt, True)
        self.add_attribute(txt, 'markup', 1)

        entry = self.child
        entry.set_icon_from_pixbuf(0, icons.Menu.get_status_pixbuf(STAT_ON))
        entry.set_icon_activatable(0, False)
        entry.set_activate_signal('activate')
        entry.connect('activate', self.entry_activate_cb)
        entry.connect('focus-out-event', self.entry_activate_cb)
        entry.connect('focus-in-event', self.entry_focus_in_cb)

    def changed_cb(self, widget, *args):
        entry = self.child
        model = self.get_model()
        itr = self.get_active_iter()
        if itr:
            entry.set_icon_from_pixbuf(0, icons.Menu.get_status_pixbuf(model.get_value(itr, 0)))
            self.current_status = model.get_value(itr, 0)
        if itr and model.get_value(itr, 3):
            self.child.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('#CCCCCC'))
            self.child.set_sensitive(model.get_value(itr, 4))
        else:
            self.child.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('#000000'))
            self.child.set_sensitive(True)
        entry.set_text(util.unescape_markup(entry.get_text()))

    def get_current_iter(self):
        entry = self.child
        model = self.get_model()
        itr = model.get_iter_first()
        while itr and model.get_value(itr, 0) != self.current_status:
            itr = model.iter_next(itr)
        while itr and model.get_value(itr, 0) == self.current_status:
            if model.get_value(itr, 1) == util.escape_markup(entry.get_text()):
                return itr
            itr = model.iter_next(itr)
        return None

    def get_default_status_iter(self):
        entry = self.child
        model = self.get_model()
        itr = model.get_iter_first()
        while itr and model.get_value(itr, 0) != self.current_status:
            itr = model.iter_next(itr)
        while itr and model.get_value(itr, 0) == self.current_status:
            if model.get_value(itr, 3):
                return itr
            itr = model.iter_next(itr)
        return None

    def entry_activate_cb(self, widget, *args):
        icon = widget.get_icon_pixbuf(0)
        txt = util.escape_markup(widget.get_text())
        model = self.get_model()
        itr = model.get_iter_first()
        while itr and self.current_status != model.get_value(itr, 0):
            itr = model.iter_next(itr)
        while itr and self.current_status == model.get_value(itr, 0):
            if txt == '' and True == model.get_value(itr, 3):
                widget.set_text(model.get_value(itr, 1))
                widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('#CCCCCC'))
                return

            if model.get_value(itr, 1) == txt:
                return
            itr = model.iter_next(itr)
        self.set_active_iter(model.insert_before(itr, [self.current_status, txt, '\x01', False, True]))

    def entry_focus_in_cb(self, widget, *args):
        model = self.get_model()
        itr = model.get_iter_first()
        icon = widget.get_icon_pixbuf(0)
        while itr and self.current_status != model.get_value(itr, 0):
            itr = model.iter_next(itr)
        while itr and self.current_status == model.get_value(itr, 0):
            if (widget.get_text(), True) == model.get(itr, 1, 3):
                widget.set_text('')
                widget.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('#000000'))
                return
            itr = model.iter_next(itr)

    def remove_current(self):
        # remove from the list if exists
        entry = self.child
        model = self.get_model()
        itr = self.get_current_iter()
        if itr and model.iter_is_valid(itr) and not model.get_value(itr, 3):
            model.remove(itr)
        else:
            return

        # and reset status to default
        itr = self.get_default_status_iter()
        if itr and model.iter_is_valid(itr):
            self.set_active_iter(itr)

class AddressList(gtk.VBox):
    def __init__(self, text):
        gtk.VBox.__init__(self)
        self._build(text)

    def _build(self, text):
        ts = gtk.ListStore(str)
        tv = gtk.TreeView(ts)
        col = gtk.TreeViewColumn('addr')
        tv.append_column(col)
        cell = gtk.CellRendererText()
        col.pack_start(cell, True)
        col.add_attribute(cell, 'text', 0)
        col.set_sort_column_id(0)
        col.set_visible(True)
        tv.set_search_column(0)
        tv.get_selection().set_mode(gtk.SELECTION_SINGLE)
        tv.set_reorderable(False)
        tv.set_headers_visible(False)
        tv.show()

        def remove_item(w, e, lv):
            sel = lv.get_selection()
            model, itr = sel.get_selected()
            if itr:
                model.remove(itr)

        def append_item(w, e, lv, ent):
            item = ent.get_text()
            if not ipmsg.util.verify_ip(item):
                return
            model = lv.get_model()
            itr = model.get_iter_first()
            while itr:
                if model.get_value(itr, 0) == item:
                    return
                itr = model.iter_next(itr)
            model.append([item])

        hbox = gtk.HBox()
        hbox.show()
        ent = gtk.Entry(100)
        ent.show()
        hbox.pack_start(ent, True, True)
        btn = gtk.Button(label=' Add ')
        btn.connect('button_press_event', append_item, tv, ent)
        btn.show()
        hbox.pack_end(btn, False, False)
        lbl = gtk.Label(text)
        lbl.show()
        self.pack_start(lbl, False, False)
        self.pack_start(hbox, False, False)
        self.pack_start(tv, True, True)
        btn = gtk.Button(label='Remove')
        btn.connect('button_press_event', remove_item, tv)
        btn.show()
        hbox = gtk.HBox()
        hbox.show()
        hbox.pack_end(btn, False, False)
        self.pack_end(hbox, False, False)

        def list_clicked(w, ent):
            model = w.get_model()
            sel = w.get_selection()
            model, itr = sel.get_selected()
            if itr:
                item = model.get_value(itr, 0)
                ent.set_text(item)

        tv.connect('cursor-changed', list_clicked, ent)
        self.tv = tv

    def get_treeview(self):
        return self.tv

class DoubleColumn(gtk.Table):
    def __init__(self, rows=1):
        gtk.Table.__init__(self, 2, rows)
        self.set_row_spacings(5)
        self.set_col_spacings(5)
        self.dirty = False

    def pack(self, widgets_tuple, row_cnt=1):
        start = self.dirty and self.get_property('n-rows') or 0
        self.resize(start + row_cnt, 2)
        self.dirty = True

        for i, widgets in enumerate(widgets_tuple):
            hbox = gtk.HBox()
            hbox.set_spacing(6)
            hbox.show()
            for w, expand in widgets:
                hbox.pack_start(w, expand, expand)
                w.show()
            vbox = gtk.VBox()
            vbox.show()
            vbox.pack_start(hbox, True, True)
            self.attach(vbox, i, i + 1, start, start + row_cnt, i == 0 and gtk.FILL or gtk.FILL|gtk.EXPAND)

class Page(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        self.tables = []

    def pack(self, pos=0, *widgets):
        hbox = gtk.HBox()
        hbox.set_spacing(6)
        hbox.show()
        for w, expand in widgets:
            hbox.pack_start(w, expand, expand)
            w.show()
        vbox = gtk.VBox()
        vbox.show()
        vbox.pack_start(hbox, True, True)
        if pos > 0:
            ali = gtk.Alignment(xscale=1.0)
            ali.set_padding(0, 0, pos*12, 0)
            ali.show()
            ali.add(vbox)
            self.pack_start(ali, True, True)
        else:
            self.pack_start(vbox, True, True)

    def add_table(self, rows=1):
        tbl = DoubleColumn(rows)
        tbl.show()
        self.pack_start(tbl, False, False)
        self.tables.append(tbl)
        return tbl

class CategoryPanel(gtk.ScrolledWindow):
    pages_data = {}
    pages = {}
    widgets = {}
    items = {}
    parent_dialog = None

    def __init__(self, parent):
        self.parent_dialog = parent
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        frm = gtk.Frame()
        frm.show()
        frm.set_border_width(0)
        frm.set_shadow_type(gtk.SHADOW_NONE)
        self.vbox = gtk.VBox()
        self.vbox.show()
        frm.add(self.vbox)
        self.vbox.set_spacing(10)
        self.pages = {}
        self.add_with_viewport(frm)

    def add_page(self, name, text=''):
        if self.pages.has_key(name):
            return self.pages[name]
        page = Page()
        page.show()
        page.set_spacing(5)
        if len(text) > 0:
            item = gtk.MenuItem(text)
            item.select()
            item.show()
            page.pack_start(item, False, False)
        self.vbox.pack_start(page, False, False)
        self.pages[name] = page
        return page

    def get_widget(self, name):
        return self.items[name].get_widget()

    def get_item(self, name):
        return self.items[name]

    def build_page(self, page_name, page_title, item_list):
        page = self.add_page(page_name, page_title)
        for item_tuple in item_list:
            pos = item_tuple[0]
            items = item_tuple[1:]
            for item in items:
                if item:
                    item.prepare()
            page.pack(pos, *[(item.get_widget(), item.get_should_expand()) for item in items])
            for item in items:
                if item and item.name:
                    self.widgets[item.name] = item.get_widget()
                    self.items[item.name] = item
 
    def build_table(self, tbl, item_list):
        for item_tuple in item_list:
            nrows = item_tuple[0]
            items = item_tuple[1:]
            for item in items:
                if item:
                    item.prepare()
            items_left = [(item.get_widget(), item.get_should_expand()) for item in items[:1] if item]
            items_right = [(item.get_widget(), item.get_should_expand()) for item in items[1:] if item]
            tbl.pack((items_left, items_right), nrows)
            for item in items:
                if item and item.name:
                    self.widgets[item.name] = item.get_widget()
                    self.items[item.name] = item
 
    def build_pages(self):
        for page_name, items in self.pages_data.items():
            page_title, item_list = items
            page = self.add_page(page_name, page_title)
            for pos, item in item_list:
                item.prepare()
                page.pack(pos, item.get_widget(), item.get_should_expand())
                self.widgets[item.name] = item.get_widget()
                self.items[item.name] = item
 
class ConfigWidget:
    name = ''

class ConfigItem:
    name = ''
    widget = None
    should_expand = True
    can_config = True

    def __init__(self, name, widget=None):
        self.name = name
        self.widget = widget

    def prepare(self):
        self.widget.show_all()
        self.initialize()

    def initialize(self):
        pass

    def get_widget(self):
        return self.widget

    def get_should_expand(self):
        return self.should_expand

    def get_can_config(self):
        return self.can_config

    def get(self):
        pass

    def set(self, value):
        pass

    def connect(self, widget):
        self.widget = widget

class ConfigItemButton(ConfigItem):
    should_expand = False
    can_config = False

    def __init__(self, name, text):
        btn = gtk.Button(text)
        btn.show()
        ConfigItem.__init__(self, name, btn)

class ConfigItemLabel(ConfigItem):
    should_expand = False
    can_config = False

    def __init__(self, text):
        lbl = gtk.Label(text)
        lbl.show()
        ConfigItem.__init__(self, '', lbl)

class ConfigItemHotkey(ConfigItem):
    should_expand = True
    can_config = True

    def __init__(self, name):
        lbl = gtk.Label()
        lbl.show()
        ConfigItem.__init__(self, name, lbl)

    def set(self, value):
        self.widget.set_text(value)

    def get(self):
        return self.widget.get_text()

class ConfigItemTextView(ConfigItem):
    def __init__(self, name):
        txt = MultiEntry()
        txt.show()
        txt.invoke('set_resize_mode', gtk.RESIZE_PARENT)
        ConfigItem.__init__(self, name, txt)

    def set(self, value):
        self.widget.set_text(value)

    def get(self):
        return self.widget.get_text()

class ConfigItemTextEntry(ConfigItem):
    def __init__(self, name, max_length):
        ent = gtk.Entry(0)
        ent.set_width_chars(max_length)
        ent.show()
        ent.set_text(settings[name])
        ConfigItem.__init__(self, name, ent)

    def set(self, value):
        self.widget.set_text(value)

    def get(self):
        return self.widget.get_text()

class ConfigItemSpinButton(ConfigItem):
    def __init__(self, name):
        adj = gtk.Adjustment(10.0, 1.0, 60.0, 1.0, 5.0, 0.0)
        spin = gtk.SpinButton(adj, 0, 0)
        spin.set_wrap(False)
        spin.show()
        spin.set_value(settings[name])
        ConfigItem.__init__(self, name, spin)

    def set(self, value):
        self.widget.set_value(value)

    def get(self):
        return self.widget.get_value_as_int()

class ConfigItemCheckBox(ConfigItem):
    def __init__(self, name, text):
        widget = gtk.CheckButton(label=text)
        widget.set_active(True)
        widget.show()
        ConfigItem.__init__(self, name, widget)

    def set(self, value):
        self.widget.set_active(value)

    def get(self):
        return self.widget.get_active()

class ConfigItemComboEntry(ConfigItem):
    def __init__(self, name):
        widget = gtk.combo_box_entry_new_text()
        widget.show()
        ConfigItem.__init__(self, name, widget)

    def set(self, value):
        self.widget.child.set_text(value)

    def get(self):
        return self.widget.child.get_text()

class ConfigItemStatusBox(ConfigItem):
    def __init__(self, name):
        widget = StatusBox()
        widget.show()
        ConfigItem.__init__(self, name, widget)

    def refresh(self):
        stat = self.get()
        self.set((1, ''))
        self.set(stat)

    def set(self, (stat, msg)):
        self.widget.child.set_text(msg)
        self.widget.child.set_icon_from_pixbuf(0, icons.Menu.get_status_pixbuf(stat))
        self.widget.current_status = stat
        assert self.widget.child.activate()

    def get(self):
        stat = self.widget.current_status
        model = self.widget.get_model()
        itr = self.widget.get_active_iter()
        if itr:
            if model.get_value(itr, 3) and model.get_value(itr, 0) != STAT_AFK:
                return (stat, '')
            else:
                return (stat, self.widget.child.get_text())
        return (stat, self.widget.child.get_text())

class ConfigItemStatusList(ConfigItem):
    def __init__(self, name):
        ConfigItem.__init__(self, name, None)

    def set(self, values):
        model = self.widget.get_model()
        model.clear()
        model.append([STAT_ON, 'On', '', True, True])
        model.append([STAT_AFK, 'Afk', '', True, True])
        model.append([STAT_INVISIBLE, 'Invisible', '', True, False])
        model.append([STAT_OFF, 'Off', '', True, False])
        for row in values:
            stat, msg, autoreply_msg = row
            msg = util.escape_markup(msg)
            model.append([stat, msg, autoreply_msg, False, stat in (STAT_ON, STAT_AFK),])

    def get(self):
        rslt = []
        model = self.widget.get_model()
        itr = model.get_iter_first()
        while itr:
            if not model.get_value(itr, 3):
                curr_tuple = list(model.get(itr, 0, 1, 2))
                curr_tuple[1] = util.unescape_markup(curr_tuple[1])
                curr_tuple[2] = curr_tuple[2]
                rslt.append(curr_tuple)
            itr = model.iter_next(itr)
        return rslt

class ConfigItemGroupList(ConfigItem):
    def __init__(self, name):
        ConfigItem.__init__(self, name, None)

    def set(self, value):
        model = self.widget.get_model()
        model.clear()
        for x in settings['group_list']:
            model.append([x])

    def get(self):
        return settings['group_list']

class ConfigItemAddressList(ConfigItem):
    def __init__(self, name, text):
        vbox = AddressList(text)
        vbox.show()
        ConfigItem.__init__(self, name, vbox)

    def set(self, values):
        model = self.widget.get_treeview().get_model()
        model.clear()
        for v in values:
            model.append([v])

    def get(self):
        rslt = []
        model = self.widget.get_treeview().get_model()
        itr = model.get_iter_first()
        while itr:
            rslt.append(model.get_value(itr, 0))
            itr = model.iter_next(itr)
        return rslt

class CommonPanel(CategoryPanel):
    def __init__(self, parent):
        CategoryPanel.__init__(self, parent)
        self.pages_data = {
            'user': ['Personal Information',
                 (1, ConfigItemLabel('User'),
                     ConfigItemTextEntry('user_name', 40)),
                 (1, ConfigItemLabel('Group'),
                     ConfigItemComboEntry('group_name')),
                 (1, None,
                     ConfigItemCheckBox('use_status_as_group', 'Use status as group')),
                 (1, ConfigItemLabel('Status'),
                     ConfigItemStatusBox('stat_msg')),
                 (1, None,
                     ConfigItemCheckBox('enable_auto_reply', 'Enable auto-reply')),
                 (16, None,
                     ConfigItemTextView('auto_reply_msg')),
                 (1, None,
                     ConfigItemButton('btn_remove_status', 'Remove')),
            ]
        }
        page_title = self.pages_data['user'][0]
        item_list = self.pages_data['user'][1:]
        page_user = self.add_page('user', 'Personal Information')
        tbl = page_user.add_table()
        self.build_table(tbl, item_list)
        self._build()

    def _build(self):
        stat_list = ConfigItemStatusList('status_list')
        stat_list.connect(self.widgets['stat_msg'])
        self.items['status_list'] = stat_list

        group_list = ConfigItemGroupList('group_list')
        group_list.connect(self.widgets['group_name'])
        self.items['group_list'] = group_list

        def toggle_group_status(widget, *args):
            active = widget.get_active()
            cmb_group = self.widgets['group_name']
            cmb_group.set_sensitive(not active)

        self.widgets['use_status_as_group'].connect('toggled', toggle_group_status)
        self.widgets['use_status_as_group'].set_active(False)

        item_name = 'auto_reply_msg'
        txt = self.widgets[item_name]
        txt.invoke('set_editable', True)
        txt.show()

        cmb_status = self.widgets['stat_msg']

        btn_remove_status = self.widgets['btn_remove_status']
        def on_remove_status(widget, event, *args):
            cmb_status.remove_current()

        btn_remove_status.set_visible(False)
        btn_remove_status.connect('button_press_event', on_remove_status)

        def changed_cb(widget, *args):
            entry = widget.child
            model = widget.get_model()
            itr = widget.get_active_iter() or widget.get_current_iter()
            if itr:
                auto_reply_msg = ''
                if model.get_value(itr, 4):
                    auto_reply_msg = model.get_value(itr, 2)
                    txt.invoke('set_sensitive', True)
                    self.widgets['enable_auto_reply'].set_visible(True)
                else:
                    txt.invoke('set_sensitive', False)
                    self.widgets['enable_auto_reply'].set_visible(False)
                if auto_reply_msg != '\x01':
                    txt.set_text(auto_reply_msg)

            itr = widget.get_current_iter()
            if itr and model.iter_is_valid(itr):
                btn_remove_status.set_visible(not model.get_value(itr, 3))
            else:
                btn_remove_status.set_visible(False)
 
        def focus_out_cb(widget, *args):
            model = cmb_status.get_model()
            itr = cmb_status.get_active_iter()
            if itr:
                model.set_value(itr, 2, txt.get_text())

        cmb_status.child.connect_after('focus-out-event', focus_out_cb)
        cmb_status.connect_after('changed', changed_cb)

        def auto_reply_save_cb(widget, *args):
            model = cmb_status.get_model()
            itr = cmb_status.get_active_iter()
            if itr and model.get_value(itr, 4):
                model.set_value(itr, 2, txt.get_text())

        txt.invoke('connect', 'focus-out-event', auto_reply_save_cb)

        def enable_auto_reply_toggle_cb(widget, *args):
            txt.invoke('set_editable', widget.get_active())
            txt.invoke('set_sensitive', widget.get_active())
            txt.invoke('set_visible', widget.get_active())

        self.widgets['enable_auto_reply'].connect('clicked', enable_auto_reply_toggle_cb)

class MessagePanel(CategoryPanel):
    def __init__(self, parent):
        CategoryPanel.__init__(self, parent)
        self.pages_data = {
            'sending': ['Sending / Replying',
                (0, ConfigItemCheckBox('always_use_utf8', 'Use UTF-8 by default')),
                (0, ConfigItemCheckBox('grouping', 'Show contact list grouping by group')),
                (0, ConfigItemCheckBox('do_readmsg_chk', 'Notify me when my message is read(for sealed messages)')),
                (0, ConfigItemCheckBox('default_seal_msg', 'By default seal message')),
                (0, ConfigItemCheckBox('default_quote_msg', 'By default quote message when reply')),
                (0, ConfigItemCheckBox('keep_recv_window_when_reply', 'Keep the receiving message window visible when replying')),
                (0, ConfigItemCheckBox('default_webshare', 'By default use http share instead of file transfer')),
                (0, ConfigItemCheckBox('notify_error', 'Message delivery error notification')),
                (0, ConfigItemLabel('Timeout'),
                    ConfigItemSpinButton('send_timeout'),
                    ConfigItemLabel('seconds')),
            ],
            'receiving': ['Receiving',
                (0, ConfigItemCheckBox('enable_notify', 'Enable notification')),
                    (1, ConfigItemCheckBox('disable_notify_afk', 'No notification when afk')),
                    (1, ConfigItemCheckBox('notify_online', 'Contacts online notification')),
                    (1, ConfigItemCheckBox('notify_offline', 'Contacts offline notification')),
                (0, ConfigItemCheckBox('enable_popup', 'Popup message')),
                    (1, ConfigItemCheckBox('non_popup_when_afk', 'Do not popup when afk')),
            ]
        }
 
        for page_name, items in self.pages_data.items():
            page_title = items[0]
            item_list = items[1:]
            self.build_page(page_name, page_title, item_list)
        self._build() 

    def _build(self):
        def toggle_enable_notify_cb(widget, *args):
            for name in ('disable_notify_afk', 'notify_online', 'notify_offline'):
                self.widgets[name].set_sensitive(widget.get_active())
        self.widgets['enable_notify'].connect('toggled', toggle_enable_notify_cb)

        def toggle_enable_popup_cb(widget, *args):
            for name in ('non_popup_when_afk',):
                self.widgets[name].set_sensitive(widget.get_active())
        self.widgets['enable_popup'].connect('toggled', toggle_enable_popup_cb)
 
class LogPanel(CategoryPanel):
    def __init__(self, parent):
        CategoryPanel.__init__(self, parent)
        self.pages_data = {
            'log': ['Log',
                (0, ConfigItemCheckBox('enable_log', 'Enable log')),
                    (1, ConfigItemCheckBox('log_use_utf8', 'Always use UTF-8')),
                    (1, ConfigItemCheckBox('log_encrypted_msg', 'Log encrypted messages in plaintext')),
                    (1, ConfigItemCheckBox('log_logon_name', 'Log contact logon name')),
                    (1, ConfigItemCheckBox('log_ip_address', 'Log contact ip address')),
                    (1, ConfigItemLabel('Log file path'), 
                        ConfigItemTextEntry('log_file_path', 40), 
                        ConfigItemButton('choose_log_file_path', 'Choose..')),
            ],
        }

        for page_name, items in self.pages_data.items():
            page_title = items[0]
            item_list = items[1:]
            self.build_page(page_name, page_title, item_list)
        self._build() 

    def _build(self):
        def toggle_cb(widget, *args):
            for name in ('log_use_utf8', 'log_encrypted_msg', 'log_logon_name', 'log_ip_address'):
                self.widgets[name].set_sensitive(widget.get_active())
        self.widgets['enable_log'].connect('toggled', toggle_cb)

        def on_choose_logfile(widget, *args):
            fcdlg = gtk.FileChooserDialog(title='Choose where to save the conversations log', 
                action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
            curr_folder = self.gconf_properties['last_log_file_path']
            fcdlg.set_current_folder(curr_folder.get())

            rsps = fcdlg.run()
            if rsps == gtk.RESPONSE_OK:
                rslt = fcdlg.get_filename()
                #if not util.verify_path(rslt):
                #    rslt = None
                # TODO: verify path
                # even verified, if read-only still need runtime check
                curr_folder.set(os.path.dirname(rslt))
            else:
                rslt = None
            fcdlg.destroy()
            self.widgets['log_file_path'].set_text(rslt)

        self.widgets['choose_log_file_path'].connect('button_press_event', on_choose_logfile)

class RulesPanel(CategoryPanel):
    def __init__(self, parent):
        CategoryPanel.__init__(self, parent)
        self.pages_data = {
            'list': ['Including / Blocking',
                (0, ConfigItemAddressList('include_list', 'Include the following'),
                    ConfigItemAddressList('block_list', 'Block the following')),
            ]
        }

        for page_name, items in self.pages_data.items():
            page_title = items[0]
            item_list = items[1:]
            self.build_page(page_name, page_title, item_list)
        self.vbox.set_child_packing(self.pages['list'], True, True, 1, gtk.PACK_START)
        self._build()

    def _build(self):
        pass
 
class HotkeyPanel(CategoryPanel):
    def __init__(self, parent):
        CategoryPanel.__init__(self, parent)
        self.pages_data = {
            'hotkey': ['Shortcuts',
                (1, ConfigItemLabel('Send'),
                    ConfigItemHotkey('hotkey_send'),
                    ConfigItemButton('btn_hotkey_send_change', 'Change...'),
                    ConfigItemButton('btn_hotkey_send_clear', 'Clear')),
                (1, ConfigItemLabel('Reply'),
                    ConfigItemHotkey('hotkey_reply'),
                    ConfigItemButton('btn_hotkey_reply_change', 'Change...'),
                    ConfigItemButton('btn_hotkey_reply_clear', 'Clear')),
            ]
        }

        items = self.pages_data['hotkey']
        page_title = items[0]
        item_list = items[1:]
        page = self.add_page('hotkey', 'Shortcuts')
        tbl = page.add_table()
        self.build_table(tbl, item_list)

        self._build()

    def _build(self):
        def on_change_hotkey_send(w, e, *args):
            changed, new_key = self.get_new_hotkey(self.items['hotkey_send'].get())
            if changed:
                self.items['hotkey_send'].set(new_key)
        self.widgets['btn_hotkey_send_change'].connect('button_press_event', on_change_hotkey_send)
        def on_clear_hotkey_send(w, e, *args):
            self.items['hotkey_send'].set('')
        self.widgets['btn_hotkey_send_clear'].connect('button_press_event', on_clear_hotkey_send)

        def on_change_hotkey_reply(w, e, *args):
            changed, new_key = self.get_new_hotkey(self.items['hotkey_reply'].get())
            if changed:
                self.items['hotkey_reply'].set(new_key)
        self.widgets['btn_hotkey_reply_change'].connect('button_press_event', on_change_hotkey_reply)
        def on_clear_hotkey_reply(w, e, *args):
            self.items['hotkey_reply'].set('')
        self.widgets['btn_hotkey_reply_clear'].connect('button_press_event', on_clear_hotkey_reply)

    def get_new_hotkey(self, default):
        dlg = HotkeyInputDialog(default, '', self.parent_dialog,  gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dlg.show()
        dlg.run()
        return dlg.result

class HotkeyInputDialog(gtk.Dialog):
    result = False, ''

    def __init__(self, default, *args, **kws):
        gtk.Dialog.__init__(self, *args, **kws)
        self.set_size_request(200, 100)
        lbl = gtk.Label('Press the keys...')
        lbl.show()
        self.vbox.pack_start(lbl)
        self.lbl = gtk.Label(default)
        self.lbl.show()
        self.vbox.pack_start(self.lbl)

        def key_press_cb(widget, event, *args):
            if event.type == gtk.gdk.KEY_PRESS:
                widget.emit_stop_by_name('key_press_event')
                keystr = ''
                if event.state & gtk.gdk.CONTROL_MASK:
                    keystr += 'Control+'
                if event.state & gtk.gdk.SHIFT_MASK:
                    keystr += 'Shift+'
                if event.state & gtk.gdk.MOD1_MASK:
                    keystr += 'Alt+'
                keystr += gtk.gdk.keyval_name(event.keyval)
                self.lbl.set_text(keystr)

        self.connect('key_press_event', key_press_cb)

        def on_response(w, id, *args):
            if id == gtk.RESPONSE_ACCEPT:
                self.result = True, self.lbl.get_text()
            else:
                self.result = False, self.lbl.get_text()
            self.destroy()
        self.connect('response', on_response)

class Preferences:
    def __init__(self):
        self.items = {}

        self.__gconf_key = 'preferences'
        self.gconf_properties = {
            'last_log_file_path' : GConfProperty(self.__gconf_key, 'last_log_file_path', '.'),
        }

        dlg = ConfigableDialog(title='Preferences', key='preferences')
        dlg.set_size_request(600, 400)

        tv = self.make_preferences_menu()

        nb = gtk.Notebook()
        nb.set_tab_pos(gtk.POS_TOP)
        nb.set_property('show-border', False)
        nb.set_property('tab-border', 5)
        nb.set_show_tabs(False)

        self.panels = [
            ('common', CommonPanel(dlg)),
            ('message', MessagePanel(dlg)),
            ('log', LogPanel(dlg)),
            ('hotkey', HotkeyPanel(dlg)),
            ('rules', RulesPanel(dlg)),
        ]
        for idx, (name, panel) in enumerate(self.panels): 
            label = gtk.Label(name.title())
            label.show()
            self.items.update(panel.items)
            panel.show()
            nb.append_page(panel, label)
            tv.get_model().append([idx, name.title()])

        nb.show()

        menu_box = gtk.VBox(False, 1)
        menu_box.pack_start(tv, True, True, 0)
        menu_box.show()

        vbox = gtk.VBox(True, 1)
        vbox.pack_start(nb, True, True, 0)
        #vbox.set_size_request(700, 400)
        vbox.show()
        hbox = gtk.HBox(False, 1)
        hbox.pack_start(menu_box, False, False, 0)
        hbox.pack_start(vbox, True, True, 0)
        hbox.show()

        dlg.vbox.pack_start(hbox, True, True, 0)

        btn_reload = gtk.Button('Restore')
        btn_reload.show()
        btn_reload.connect('button_press_event', self.do_reload)
        dlg.action_area.pack_start(btn_reload, True, True, 0)

        btn_apply = gtk.Button('Apply')
        btn_apply.show()
        btn_apply.connect('button_press_event', self.do_apply)
        dlg.action_area.pack_start(btn_apply, True, True, 0)

        btn_ok = gtk.Button('OK')
        btn_ok.show()
        btn_ok.connect('button_press_event', self.do_ok)
        dlg.action_area.pack_end(btn_ok, True, True, 0)

        btn_cancel = gtk.Button('Cancel')
        btn_cancel.show()
        btn_cancel.connect('button_press_event', self.do_close)
        dlg.action_area.pack_end(btn_cancel, True, True, 0)

        tv.connect('cursor-changed', self.show_category, nb)

        tv.get_selection().select_path((0))

        self.dlg = dlg
        self.disable_escape()

        self.dlg.connect('delete_event', self.dlg.hide_on_delete)

    def make_preferences_menu(self):
        ts = gtk.ListStore(int, str)
        tv = gtk.TreeView(ts)
        tv.set_headers_visible(False)

        cols = [('', False), ('', True)]

        for (idx, (header, visible)) in enumerate(cols):
            col = gtk.TreeViewColumn(header)
            cell = gtk.CellRendererText()
            col.pack_start(cell, True)
            col.add_attribute(cell, 'text', idx)
            col.set_sort_column_id(idx)
            col.set_visible(visible)
            tv.append_column(col)

        tv.set_search_column(0)
        tv.set_reorderable(False)
        tv.show()

        return tv

    def show(self, on_save_cb=None):
        self.on_save_cb = on_save_cb or (lambda : None)
        self.load()
        self.dlg.present()
        self.items['stat_msg'].get_widget().grab_focus()
        self.items['stat_msg'].refresh()

    def load(self):
        for name, item in self.items.items():
            if item.get_can_config() and item.name and item.widget:
                item.set(settings[name])

    def disable_escape(self):
        def key_press_cb(widget, event, *args):
            if event.type == gtk.gdk.KEY_PRESS and event.keyval == gtk.gdk.keyval_from_name('Escape'):
                widget.emit_stop_by_name('key_press_event')

        self.dlg.connect('key_press_event', key_press_cb)

    def show_category(self, tv, nb):
        sel = tv.get_selection()
        def __show_category(model, path, itr, nb):
            id = model.get_value(itr, 0)
            nb.set_current_page(id)
        sel.selected_foreach(__show_category, nb)

    def do_reload(self, widget, event):
        self.load()

    def do_apply(self, widget, event):
        self.save()

    def do_ok(self, widget, event):
        if self.save():
            self.dlg.hide()

    def do_close(self, widget, event):
        self.dlg.hide()

    def save(self):
        global settings
        tmp_settings = copy.copy(settings)
        for name, item in self.items.items():
            if item.get_can_config() and item.name and item.widget:
                tmp_settings[name] = item.get()
        rslt = tmp_settings.get_error()
        if not rslt:
            settings = copy.copy(tmp_settings)
            settings.save()
            self.on_save_cb()
            return True
        else:
            args, (error, controls) = rslt
            from pyipmsg.dialogs.message import ConfigValidationErrorDialog
            dlg = ConfigValidationErrorDialog(self.dlg, (','.join(args), error))
            dlg.show()
            dlg.run()
            dlg.destroy()
            return False

