# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango
import sys, os, os.path, copy
import re, string
from datetime import date, datetime

from ipmsg import MessageLog
from ipmsg.config import settings

from pyipmsg import util
from pyipmsg.widgets import ConversationView
from pyipmsg import icons
from pyipmsg.dialogs.configable import ConfigableDialog
from pyipmsg.conf.settings import SettingsDialog, GConfProperty
from pyipmsg.conf.widgets import GConfFontButton, GConfColorButton

import logging
logger = logging.getLogger('LogViewer')

class ContactList(gtk.TreeView):
    def __init__(self):
        ts = gtk.ListStore(str, str)
        gtk.TreeView.__init__(self, ts)
        self._build_model()

    def _build_model(self):
        self.__cols = [('Contact', True), ('id', False), ]
        for idx, (header, visible) in enumerate(self.__cols):
            col = gtk.TreeViewColumn(header)
            self.append_column(col)
            cell = gtk.CellRendererText()
            col.pack_start(cell, True)
            col.add_attribute(cell, 'text', idx)
            col.set_sort_column_id(idx)
            col.set_visible(visible)

        self.set_search_column(0)
        self.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.set_reorderable(True)
        self.set_headers_visible(False)

    def update_list(self, contacts):
        model = self.get_model()
        model.clear()
        model.append(['All Contacts', '__all__'])
        for contact in contacts:
            model.append([contact, contact])
        self.get_selection().select_path(0)

    def get_selected_contact(self):
        model, itr = self.get_selection().get_selected()
        if not itr:
            return '__all__'
        contact, id = model.get(itr, 0, 1)
        if id == '__all__':
            return '__all__'
        else:
            return contact

class DateFilterScale(gtk.HScale):
    ALL, YEAR, MONTH, DAY = 0, 0.1, 0.2, 0.3
    TEXT = { ALL   : 'Any time',
             YEAR  : 'Selected year',
             MONTH : 'Selected month',
             DAY   : 'Selected date', }

    def __init__(self):
        adj = gtk.Adjustment(self.ALL, self.ALL, self.DAY, 0.1, 0, 0)
        gtk.HScale.__init__(self, adj)
        self.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.connect('format-value', self._format_value)

    def _format_value(self, widget, value):
        return self.TEXT[value]

    def is_all(self):
        return self.get_value() == self.ALL

    def is_year(self):
        return self.get_value() == self.YEAR

    def is_month(self):
        return self.get_value() == self.MONTH

    def is_day(self):
        return self.get_value() == self.DAY

class LogViewerSettings(SettingsDialog):
    def _build(self):
        SettingsDialog._build(self)

        prop = self.parent.get_property('title-from-font')
        def on_changed_cb(desc):
            self.parent.txt_log.styles['title-from']['font-desc'] = desc
            self.parent.txt_log.reload_styles()
        btn_title_from_font = GConfFontButton(prop, on_changed_cb)

        prop = self.parent.get_property('title-from-color')
        def on_changed_cb(color):
            self.parent.txt_log.styles['title-from']['foreground'] = color.to_string()
            self.parent.txt_log.reload_styles()
        btn_title_from_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('title-from-bgcolor')
        def on_changed_cb(color):
            self.parent.txt_log.styles['title-from']['paragraph-background'] = color.to_string()
            self.parent.txt_log.reload_styles()
        btn_title_from_bgcolor = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('title-to-font')
        def on_changed_cb(desc):
            self.parent.txt_log.styles['title-to']['font-desc'] = desc
            self.parent.txt_log.reload_styles()
        btn_title_to_font = GConfFontButton(prop, on_changed_cb)

        prop = self.parent.get_property('title-to-color')
        def on_changed_cb(color):
            self.parent.txt_log.styles['title-to']['foreground'] = color.to_string()
            self.parent.txt_log.reload_styles()
        btn_title_to_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('title-to-bgcolor')
        def on_changed_cb(color):
            self.parent.txt_log.styles['title-to']['paragraph-background'] = color.to_string()
            self.parent.txt_log.reload_styles()
        btn_title_to_bgcolor = GConfColorButton(prop, on_changed_cb)

        self.add_page('From', [('Title Font', btn_title_from_font), ('Color', btn_title_from_color), ('Background', btn_title_from_bgcolor)])
        self.add_page('To', [('Title Font', btn_title_to_font), ('Color', btn_title_to_color), ('Background', btn_title_to_bgcolor)])

        prop = self.parent.get_property('link-color')
        def on_changed_cb(color):
            self.parent.txt_log.link['foreground'] = color.to_string()
            self.parent.txt_log.recognize_url()
        btn_link_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('link-bgcolor')
        def on_changed_cb(color):
            self.parent.txt_log.link['background'] = color.to_string()
            self.parent.txt_log.recognize_url()
        btn_link_bgcolor = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('link-hover-color')
        def on_changed_cb(color):
            self.parent.txt_log.hover['foreground'] = color.to_string()
            self.parent.txt_log.recognize_url()
        btn_hover_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('link-hover-bgcolor')
        def on_changed_cb(color):
            self.parent.txt_log.hover['background'] = color.to_string()
            self.parent.txt_log.recognize_url()
        btn_hover_bgcolor = GConfColorButton(prop, on_changed_cb)

        self.add_page('Url', [('Color', btn_link_color), ('Background', btn_link_bgcolor),
                              ('Hover Color', btn_hover_color), ('Hover Background', btn_hover_bgcolor)])

class LogViewerDialog(ConfigableDialog):
    def __init__(self):
        ConfigableDialog.__init__(self, key='logviewer', title='Previous Conversations')
        self.set_size_request(800, 600)

        self.contacts_list = ContactList()
        self.contacts_list.show()

        self.group_list = ContactList()
        self.group_list.show()

        self.nb = gtk.Notebook()
        self.nb.show()
        self.nb.set_tab_pos(gtk.POS_TOP)
        self.nb.set_property('show-border', False)
        self.nb.set_property('tab-border', 2)
        self.nb.set_show_tabs(True)

        sw = gtk.ScrolledWindow()
        sw.show()
        sw.set_property('can-focus', False)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(self.contacts_list)
        lbl = gtk.Label('Contact')
        lbl.show()
        self.nb.append_page(sw, lbl)

        sw = gtk.ScrolledWindow()
        sw.show()
        sw.set_property('can-focus', False)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(self.group_list)
        lbl = gtk.Label('Group')
        lbl.show()
        self.nb.append_page(sw, lbl)

        self.nb.set_property('can-focus', False)

        self.calendar = gtk.Calendar()
        self.calendar.show()

        self.filter_date = DateFilterScale()
        self.filter_date.show()
        self.filter_date.set_value(DateFilterScale.DAY)

        nav_box = gtk.VBox(False, 1)
        nav_box.pack_end(self.calendar, False, False, 2)
        nav_box.pack_end(self.filter_date, False, False, 2)
        nav_box.pack_end(self.nb, True, True, 2)
        nav_box.show()

        txt_log = ConversationView(rules=[])
        txt_log.show()
        txt_log.invoke('set_editable', False)
        self.txt_log = txt_log

        def url_clicked_cb(widget, type, url, btn):
            if btn == 1:
                util.launch_file(url)
        txt_log.connect('anchor-clicked', url_clicked_cb)

        txt_search = gtk.Entry()
        txt_search.set_icon_from_pixbuf(0, icons.Toolbar.get_pixbuf('search'))
        txt_search.set_icon_activatable(0, False)
        txt_search.show()
        self.txt_search = txt_search

        hbox_search = gtk.HBox(False, 1)
        hbox_search.show()
        hbox_search.pack_start(txt_search, True, True, 5)

        vbox = gtk.VBox(False, 1)
        vbox.pack_end(txt_log, True, True, 5)
        vbox.pack_start(hbox_search, False, False, 5)
        vbox.show()

        hbox = gtk.HBox(False, 1)
        hbox.pack_start(nav_box, False, False, 5)
        hbox.pack_start(vbox, True, True, 10)
        hbox.show()

        self.vbox.pack_start(hbox, True, True, 0)

        btn = gtk.Button('Launch')
        btn.set_tooltip_markup('Open the log file using external editor')
        btn.show()
        self.action_area.pack_start(btn, True, True, 0)
        self.btn_launch = btn

        btn = gtk.Button('Reload')
        btn.set_tooltip_markup('Reload from file')
        btn.show()
        self.action_area.pack_start(btn, True, True, 0)
        self.btn_reload = btn

        btn_close = gtk.Button('Close')
        btn_close.show()
        btn_close.connect('button_press_event', lambda w, e: self.hide())
        self.action_area.pack_end(btn_close, True, True, 0)
        self.btn_close = btn_close

        self.update_gconf()

    def update_gconf(self):
        for cate in ('title-from', 'title-to'):
            font = self.get_gconf('%s-font' % cate)
            if font:
                desc = pango.FontDescription(font)
                self.txt_log.styles[cate]['font-desc'] = desc
            color = self.get_gconf('%s-color' % cate)
            if color:
                self.txt_log.styles[cate]['foreground'] = color
            color = self.get_gconf('%s-bgcolor' % cate)
            if color:
                self.txt_log.styles[cate]['paragraph-background'] = color

        color = self.get_gconf('link-color')
        if color:
            self.txt_log.link['foreground'] = color

        color = self.get_gconf('link-bgcolor')
        if color:
            self.txt_log.link['background'] = color

        color = self.get_gconf('link-hover-color')
        if color:
            self.txt_log.hover['foreground'] = color

        color = self.get_gconf('link-hover-bgcolor')
        if color:
            self.txt_log.hover['background'] = color

        self.txt_log.recognize_url()
        self.txt_log.reload_styles()

    def init_gconf(self):
        self.add_gconf_property('title-from-font', '')
        self.add_gconf_property('title-from-color', gtk.gdk.Color(0, 0, 0).to_string())
        self.add_gconf_property('title-from-bgcolor', gtk.gdk.Color(65535, 65535, 65535).to_string())
        self.add_gconf_property('title-to-font', '')
        self.add_gconf_property('title-to-color', gtk.gdk.Color(0, 0, 0).to_string())
        self.add_gconf_property('title-to-bgcolor', gtk.gdk.Color(65535, 65535, 65535).to_string())
        self.add_gconf_property('link-color', 'blue')
        self.add_gconf_property('link-bgcolor', 'white')
        self.add_gconf_property('link-hover-color', 'red')
        self.add_gconf_property('link-hover-bgcolor', 'gray')
        self.add_gconf_property('link-active-color', 'red')
        self.add_gconf_property('link-active-bgcolor', 'gray')

    def show_settings(self):
        dlg = LogViewerSettings(self.key, parent=self)
        dlg.run()

class LogViewer:
    def __init__(self):
        self.dlg = LogViewerDialog()
        self.dlg.contacts_list.connect('cursor-changed', self.update)
        self.dlg.group_list.connect('cursor-changed', self.update)
        self.dlg.nb.connect('switch-page', self.update)
        self.dlg.calendar.connect('day_selected', self.update_content)
        self.dlg.calendar.connect('month_changed', self.update)
        self.dlg.calendar.connect('next_month', self.update)
        self.dlg.calendar.connect('next_year', self.update)
        self.dlg.calendar.connect('prev_month', self.update)
        self.dlg.calendar.connect('prev_year', self.update)
        self.dlg.filter_date.connect('value-changed', self.update)
        self.dlg.txt_search.connect('activate', self.update_highlight)
        self.dlg.btn_launch.connect('pressed', self.on_launch_file)
        self.dlg.btn_reload.connect('pressed', self.on_reload)
        self.dlg.connect('delete_event', self.dlg.hide_on_delete)

    def load(self, log_file):
        self.logs = []
        self.logs_by_date = {}
        self.logs_by_addr = {}
        self.logs_by_group = {}
        curr_content = ''
        for line in file(log_file, 'rb'):
            if len(line) > 0 and line[0] == '=':
                if curr_content:
                    self.logs.append(MessageLog.parse(curr_content))
                    curr_content = ''
            else:
                curr_content += line

        if curr_content:
            self.logs.append(MessageLog.parse(curr_content))

        for log in self.logs:
            day = datetime.strftime(log.time, '%Y%m%d')
            if day not in self.logs_by_date:
                self.logs_by_date[day] = []
            self.logs_by_date[day].append(log)

            addr = log.contact_host
            if addr not in self.logs_by_addr:
                self.logs_by_addr[addr] = []
            self.logs_by_addr[addr].append(log)

            addr = log.contact_group
            if addr not in self.logs_by_group:
                self.logs_by_group[addr] = []
            self.logs_by_group[addr].append(log)

    def update(self, widget, *args):
        self.update_calendar()
        self.update_content(widget)

    def update_calendar(self):
        year, month, day = self.dlg.calendar.get_date()
        today = date(year, month + 1, day)
        curr_ym = date.strftime(today, '%Y%m')
        self.dlg.calendar.clear_marks()
        for d in range(31):
            try:
                ymd = date.strftime(date(year, month + 1, d + 1), '%Y%m%d')
            except ValueError:
                break
            if ymd in self.logs_by_date:
                self.dlg.calendar.mark_day(d + 1)

    def update_content(self, widget, *args):
        if self.dlg.filter_date.is_all():
            logs = self.logs[:]
        else:
            year, month, day = self.dlg.calendar.get_date()
            today = date(year, month + 1, day)
            curr_ymd = date.strftime(today, '%Y%m%d')
            if self.dlg.filter_date.is_year():
                logs = reduce((lambda x, y: x + y), [self.logs_by_date[k] for k in self.logs_by_date.keys() if k[:4] == curr_ymd[:4]] or [[]])
            elif self.dlg.filter_date.is_month():
                logs = reduce((lambda x, y: x + y), [self.logs_by_date[k] for k in self.logs_by_date.keys() if k[:6] == curr_ymd[:6]] or [[]])
            elif self.dlg.filter_date.is_day():
                logs = curr_ymd in self.logs_by_date and self.logs_by_date[curr_ymd] or {}
            else:
                logs = {}

        if self.dlg.nb.get_current_page() == 0:
            curr_contact = self.dlg.contacts_list.get_selected_contact()
            if curr_contact != '__all__':
                logs_contact = curr_contact in self.logs_by_addr and self.logs_by_addr[curr_contact] or {}
                logs = [log for log in logs if log in logs_contact]
        else:
            curr_contact = self.dlg.group_list.get_selected_contact()
            if curr_contact != '__all__':
                logs_contact = curr_contact in self.logs_by_group and self.logs_by_group[curr_contact] or {}
                logs = [log for log in logs if log in logs_contact]

        self.dlg.txt_log.clear()
        for log in logs: 
            self.dlg.txt_log.append_header_line()
            title = '%s: %s(%s) - %s/%s' % (log.io and 'From' or 'To', log.contact_name, log.contact_group, log.contact_host, log.contact_addr)
            self.dlg.txt_log.append_title(log.io, title)
            self.dlg.txt_log.append_header_line()
            hms = datetime.strftime(log.time, '%Y/%m/%d %H:%M:%S ')
            self.dlg.txt_log.append_time(log.io, hms)
            self.dlg.txt_log.append_spacing()
            self.dlg.txt_log.append_body(log.io, log.msg)
            self.dlg.txt_log.append_body(log.io, ','.join(log.attachments))

        self.update_highlight(self.dlg.txt_search)

    def update_highlight(self, widget, *args):
        keyword = self.dlg.txt_search.get_text()
        self.dlg.txt_log.set_highlight(keyword)

    def on_reload(self, widget, *args):
        self.load(settings['log_file_path'])
        self.update_contacts_list()
        self.update_calendar()
        self.update_content(widget=None)

    def on_launch_file(self, widget, *args):
        fpath = settings['log_file_path']
        if not fpath:
            return
        util.launch_file(fpath)

    def update_contacts_list(self):
        self.dlg.contacts_list.update_list(list(set(log.contact_host for log in self.logs)))
        self.dlg.group_list.update_list(list(set(log.contact_group for log in self.logs)))

    def show(self):
        self.load(settings['log_file_path'])
        self.update_contacts_list()
        self.update_calendar()
        self.update_content(widget=None)
        self.dlg.present()
        self.dlg.txt_search.grab_focus()

