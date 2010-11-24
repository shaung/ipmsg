# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk, gobject, gnome, pango
import os, os.path, time
import urllib, re
import logging, logging.config

import ipmsg
from ipmsg.config import settings
from ipmsg.status import *

from pyipmsg import util
from pyipmsg.widgets import MultiEntry, HyperMultiEntry
from pyipmsg import icons
from pyipmsg.dialogs.configable import ConfigableDialog
from pyipmsg.conf.settings import SettingsDialog, GConfProperty
from pyipmsg.conf.widgets import GConfFontButton, GConfColorButton, GConfCheckButton
from pyipmsg.dialogs.message import *

class ContactList(gtk.TreeView):
    def __init__(self, get_contacts_func=(lambda : []), grouping=True):
        self.get_contacts_func = get_contacts_func
        self.grouping = grouping
        self.piters = {}
        self.buffered_contacts = []

        ts = gtk.TreeStore(str, str, str, str, str, str, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf)
        gtk.TreeView.__init__(self, ts)
        self._build()

        self.connect('button_press_event', self.on_button_press_event)

        self.reload()

    def get_cols(self):
        return [('Addr', False), \
                ('User', True), \
                ('Group', not self.grouping), \
                ('Version', False), \
                ('Login', True), \
                ('Host', True),  ]

    def get_selected_contacts(self):
        sel = self.get_selection()
        if sel.count_selected_rows() == 0:
            return []

        rslt = []
        model, paths = sel.get_selected_rows()
        for path in paths:
            if len(path) == 1 and self.grouping:
                root_itr = model.get_iter(path)
                itr = model.iter_children(root_itr)
                while itr:
                    ip, port = re.split(':', model.get_value(itr, 0), 2)
                    rslt.append((ip, int(port)))
                    itr = model.iter_next(itr)
            else:
                itr = model.get_iter(path)
                ip, port = re.split(':', model.get_value(itr, 0), 2)
                rslt.append((ip, int(port)))
        return list(set(rslt))

    def select_contacts(self, *addrs):
        id_addrs = [':'.join(map(str, addr)) for addr in addrs]
        self.get_model().foreach(self._select_contact_cb, id_addrs)

    def _select_contact_cb(self, model, path, itr, id_addrs):
        if model.get_value(itr, 0) in id_addrs:
            self.get_selection().select_path(path)

    def get_normal_markup(self, value):
        return value

    def get_offline_markup(self, value):
        return '<s>%s</s>' % value

    def update_contact(self, contact, root_itr):
        id_addr = contact.get_id()
        itr = root_itr
        model = self.get_model()
        while itr:
            if model.get_value(itr, 0) == id_addr:
                get_markup = contact.has_left_for() > 0 and self.get_offline_markup or self.get_normal_markup
                model.set(itr, 1, get_markup(contact.name),
                               2, get_markup(contact.group),
                               3, get_markup(contact.version),
                               4, get_markup(contact.login),
                               5, get_markup(contact.host),
                               6, icons.Menu.get_status_pixbuf(contact.status),
                               7, contact.addr[0] in ipmsg.get_block_list() and icons.Menu.get_pixbuf('block') or None, 
                                )
                return itr
            itr = model.iter_next(itr)
        return None

    def append_contact(self, contact):
        identifer = contact.get_id()
        itr = self.get_model().append( \
            self.get_group_itr_by_name(contact.group), \
            [identifer, contact.name, contact.group, contact.version, contact.login, contact.host, None, \
             contact.addr[0] in ipmsg.get_block_list() and icons.Menu.get_pixbuf('block') or None, ])

        self.expand_to_path(self.get_model().get_path(itr))

    def append_or_update_contact(self, contact, group_itr=None):
        root_itr = group_itr or self.get_model().get_iter_first()
        if self.update_contact(contact, root_itr) is None:
            self.append_contact(contact)

    def get_group_itr_by_name(self, group):
        if not self.grouping:
            return None
        if not self.piters.has_key(group):
            return None
        return self.piters[group]

    def get_or_create_group(self, group):
        itr = self.get_group_itr_by_name(group)
        if itr is None and self.grouping:
            self.piters[group] = self.get_model().append(None, [group, '<span><big><b>%s</b></big></span>' % util.escape_markup(group), '', '', '', '', None, None])
            self.expand_row(self.get_model().get_path(self.piters[group]), True)
            return self.piters[group]
        else:
            return itr

    def _build_model(self):
        contacts = self.get_contacts_func()

        for contact in contacts:
            self.append_or_update_contact(contact, self.get_model().iter_children(self.get_or_create_group(contact.group)))

        ids = [(c.get_id(), c.group) for c in contacts]
 
        model = self.get_model()
        if self.grouping:
            itr_group = model.get_iter_first()
            while itr_group and model.iter_is_valid(itr_group):
                should_remove = True
                itr = model.iter_children(itr_group)
                while itr and model.iter_is_valid(itr):
                    if model.get(itr, 0, 2) in ids:
                        should_remove = False
                        itr = model.iter_next(itr)
                    else:
                        model.remove(itr)
                if should_remove:
                    del self.piters[unicode(model.get_value(itr_group, 0), 'utf8')]
                    model.remove(itr_group)
                else:
                    itr_group = model.iter_next(itr_group)
        else:
            itr = model.get_iter_first()
            while itr and model.iter_is_valid(itr):
                if model.get(itr, 0, 2) in ids:
                    itr = model.iter_next(itr)
                else:
                    model.remove(itr)

    def _build(self):
        for idx, (header, visible) in enumerate(self.get_cols()):
            cell = gtk.CellRendererText()
            col = gtk.TreeViewColumn(header, cell, markup=idx)
            if idx == 1:
                cell_pixbuf = gtk.CellRendererPixbuf()
                col.pack_start(cell_pixbuf, False)
                col.add_attribute(cell_pixbuf, 'pixbuf', 7)
            self.append_column(col)
            if idx == 1:
                cell_pixbuf = gtk.CellRendererPixbuf()
                col.pack_start(cell_pixbuf, False)
                col.add_attribute(cell_pixbuf, 'pixbuf', 6)
            col.add_attribute(cell, 'text', idx)
            col.set_sort_column_id(idx)
            col.set_visible(visible)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)

        col = gtk.TreeViewColumn('status icon')
        self.append_column(col)
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, True)
        col.add_attribute(cell, 'pixbuf', 6)
        col.set_sort_column_id(6)
        col.set_visible(False)

        self.set_search_column(1)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.set_reorderable(True)
        self.expand_all()
        self.set_level_indentation(0)
        self.set_property('rubber-banding', False)
        self.set_property('reorderable', False)

    def toggle_grouping(self):
        self.grouping = not self.grouping
        self.get_column(2).set_visible(not self.grouping)
        self.get_model().clear()
        self.piters = {}
        self.reload()

    def reload(self, get_contacts_func=None, toggle_grouping=False):
        if get_contacts_func:
            self.get_contacts_func = get_contacts_func

        self._build_model()

    def make_context_menu(self, itr):
        menu = gtk.Menu()
        menu.show()
        model = self.get_model()
        contact_id = model.get_value(itr, 0).split(':')[0]
        if contact_id in ipmsg.get_block_list():
            item = gtk.MenuItem('Unblock', False)
            def on_handle(w, *args):
                model.set(itr, 7, None)
                settings['block_list'] = [ip for ip in settings['block_list'] if ip != contact_id]
                settings.save()
                ipmsg.update_block_list()
        else:
            item = gtk.MenuItem('Block', False)
            def on_handle(w, *args):
                model.set(itr, 7, icons.Menu.get_pixbuf('block'))
                settings['block_list'].append(contact_id)
                settings.save()
                ipmsg.update_block_list()
        item.connect('activate', on_handle)
        item.show()
        menu.add(item)
        return menu

    def on_button_press_event(self, treeview, event):
        if event.button == 3:
            x, y = int(event.x), int(event.y)
            time = event.time
            pathinfo = treeview.get_path_at_pos(x, y)
            if pathinfo is not None:
                path, col, cellx, celly = pathinfo
                treeview.set_cursor(path, col, 0)
                model = self.get_model()
                itr = model.get_iter(path)
                if not itr or not model.get_value(itr, 5):
                    return True
                contact_id = model.get_value(itr, 0).split(':')
                addr = (contact_id[0], int(contact_id[-1]))
                if ipmsg.get_engine().is_self(addr):
                    return
                menu = self.make_context_menu(itr)
                menu.popup( None, None, None, event.button, event.time)
            return True

class AttList(gtk.TreeView):
    __cols = ['File', 'Size', 'Fullpath', ]
    def __init__(self):
        ts = gtk.ListStore(str, str, str)
        gtk.TreeView.__init__(self, ts)

        for idx, header in enumerate(self.__cols):
            col = gtk.TreeViewColumn(header)
            self.append_column(col)
            cell = gtk.CellRendererText()
            col.pack_start(cell, True)
            col.add_attribute(cell, 'text', idx)
            col.set_sort_column_id(idx)

        self.set_search_column(0)
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.set_reorderable(True)
        self.set_headers_visible(True)
        self.show()

    def append_file(self, fname):
        def make_file_row(fname):
            return [os.path.basename(fname), os.path.isfile(fname) and str(os.path.getsize(fname)) or 'Folder', fname]

        model = self.get_model()
        itr = model.get_iter_first()
        while itr and model.iter_is_valid(itr):
            if model.get_value(itr, 2) == fname:
                return
            itr = model.iter_next(itr)
        self.get_model().append(make_file_row(fname))

    def get_selected(self):
        rslt = []
        sel = self.get_selection()
        if sel.count_selected_rows() == 0:
            return

        model, paths = sel.get_selected_rows()
        for path in paths:
            itr = model.get_iter(path)
            rslt.append(model.get_value(itr, 2))

        return rslt

    def remove_selected(self):
        sel = self.get_selection()
        if sel.count_selected_rows() == 0:
            return

        model, paths = sel.get_selected_rows()
        itrs = [model.get_iter(path) for path in paths]
        for itr in itrs:
            model.remove(itr)

class Attachments:
    def __init__(self, parent):
        self.parent = parent
        self.share_files = set([])
        self._build_dialog()
        self.__gconf_key = 'send/attachments'
        self.gconf_properties = {
            'last_file_path' : GConfProperty(self.__gconf_key, 'last_file_path', '.'),
            'last_folder_path' : GConfProperty(self.__gconf_key, 'last_folder_path', '.'),
        }

    def append(self, item):
        if item not in self.share_files:
            self.share_files.add(item)
            self.att_list.append_file(item)

    def get_all(self):
        return self.share_files

    def filter_valid_files(self, files):
        oks, errors = [], []
        for fname in files:
            try:
                ipmsg.verify_files(fname)
            except ipmsg.AttachmentError as e:
                errors.append((fname, str(e)))
            except Exception as e:
                errors.append((fname, str(e)))
            else:
                oks.append(fname)

        if errors:
            dlg = AttachmentsErrorDialog(self.dlg, errors)
            def on_error_rsps(w, id, *args):
                if id != gtk.RESPONSE_YES:
                    oks = []
                dlg.destroy()
            dlg.connect('response', on_error_rsps)
            dlg.run()

        return oks

    def _build_dialog(self):
        dlg = gtk.Dialog('Attach files', self.parent.dlg, gtk.DIALOG_DESTROY_WITH_PARENT)
        #dlg.set_transient_for(self.parent)
        dlg.set_keep_above(True)
        dlg.set_size_request(600, 300)

        att_list = AttList()
        att_list.show()
        vbox = gtk.VBox()
        vbox.show()
        vbox.pack_start(att_list, True, True, 5)
        sw = gtk.ScrolledWindow()
        sw.show()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(vbox)
        dlg.vbox.pack_start(sw, True, True, 5)

        for fname in self.share_files:
            att_list.append_file(fname)

        def do_remove_attach(w, event):
            for fname in att_list.get_selected():
                self.share_files.discard(fname)

            att_list.remove_selected()
            self.parent.update_file_summary()

        def choose_file(is_dir):
            fcdlg = gtk.FileChooserDialog(title='Open %s' % (is_dir and 'dir' or 'file'), 
                action=is_dir and gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER or gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
            fcdlg.set_select_multiple(True)
            curr_folder = self.gconf_properties[is_dir and 'last_folder_path' or 'last_file_path']
            fcdlg.set_current_folder(curr_folder.get())

            rsps = fcdlg.run()
            if rsps == gtk.RESPONSE_OK:
                rslt = fcdlg.get_filenames()
                rslt = self.filter_valid_files(rslt)
                curr_folder.set(os.path.dirname(fcdlg.get_filename()))
            else:
                rslt = None
            fcdlg.destroy()
            return rslt

        def do_add_attachments(w, event, is_dir):
            fnames = choose_file(is_dir) or []
            for fname in fnames:
                if fname and fname not in self.share_files:
                    self.share_files.add(fname)
                    att_list.append_file(fname)
            self.parent.update_file_summary()

        btn = gtk.Button('+File')
        btn.connect('button_press_event', do_add_attachments, False)
        btn.show()
        dlg.action_area.pack_start(btn)

        btn = gtk.Button('+Dir')
        btn.connect('button_press_event', do_add_attachments, True)
        btn.show()
        dlg.action_area.pack_start(btn)

        btn = gtk.Button('Remove')
        btn.connect('button_press_event', do_remove_attach)
        btn.show()
        dlg.action_area.pack_start(btn)

        btn = gtk.Button('Close')
        btn.connect('button_press_event', lambda w, e: dlg.hide())
        btn.show()
        dlg.action_area.pack_start(btn)

        dlg.drag_dest_set(gtk.DEST_DEFAULT_DROP, [('text/plain', 0, 82), ('image/*', 0, 83)], gtk.gdk.ACTION_COPY)
        dlg.connect('drag_motion', self.file_motion_cb)
        dlg.connect('drag_drop', self.file_drop_cb)
        dlg.connect('drag_data_received', self.drag_data_received)

        self.dlg = dlg
        self.dlg.connect('delete_event', self.dlg.hide_on_delete)
        self.att_list = att_list

    def file_motion_cb(self, widget, context, x, y, time):
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True

    def file_drop_cb(self, widget, context, x, y, time):
        if context.targets:
            widget.drag_get_data(context, context.targets[0], time)
            return True
        return False

    def drag_data_received(self, widget, context, x, y, data, info, time):
        if data.format != 8:
            return
        files = data.data.rstrip().split('\r\n')
        oks, errors = [], []
        for f in files:
            ext = os.path.splitext(f)[1][1:4].lower().strip()
            fname = urllib.unquote(f[7:])
            try:
                ipmsg.verify_files(fname)
            except ipmsg.AttachmentError as e:
                errors.append((fname, str(e)))
            except Exception as e:
                errors.append((fname, str(e)))
            else:
                oks.append(fname)
            finally:
                context.finish(True, False, time)

        if errors:
            dlg = AttachmentsErrorDialog(self.dlg, errors)
            def on_error_rsps(w, id, *args):
                if id == gtk.RESPONSE_YES:
                    for fname in oks:
                        self.share_files.add(fname)
                        self.att_list.append_file(fname)
                dlg.destroy()
            dlg.connect('response', on_error_rsps)
            dlg.show()
        else:
            for fname in oks:
                self.share_files.add(fname)
                self.att_list.append_file(fname)

        self.parent.update_file_summary()
 
    def run_dialog(self):
        self.dlg.present()

class SendSettings(SettingsDialog):
    def _build(self):
        SettingsDialog._build(self)

        prop = self.parent.get_property('contacts-list-font')
        on_changed_cb = lambda desc: self.parent.cl.modify_font(desc)
        btn_cl_font = GConfFontButton(prop, on_changed_cb)

        prop = self.parent.get_property('contacts-list-color')
        on_changed_cb = lambda color: self.parent.cl.modify_text(gtk.STATE_NORMAL, color)
        btn_cl_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('contacts-list-bgcolor')
        on_changed_cb = lambda color: self.parent.cl.modify_base(gtk.STATE_NORMAL, color)
        btn_cl_bgcolor = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('contacts-list-header-visible-name')
        on_changed_cb = lambda visible: self.parent.cl.get_column(1).set_visible(visible)
        chk_name = GConfCheckButton(prop, on_changed_cb, 'User')

        prop = self.parent.get_property('contacts-list-header-visible-group')
        on_changed_cb = lambda visible: self.parent.cl.get_column(2).set_visible(visible)
        chk_group = GConfCheckButton(prop, on_changed_cb, 'Group')
        chk_group.set_sensitive(not settings['grouping'])

        prop = self.parent.get_property('contacts-list-header-visible-version')
        on_changed_cb = lambda visible: self.parent.cl.get_column(3).set_visible(visible)
        chk_version = GConfCheckButton(prop, on_changed_cb, 'Version')

        prop = self.parent.get_property('contacts-list-header-visible-status')
        on_changed_cb = lambda visible: self.parent.cl.get_column(4).set_visible(visible)
        chk_login = GConfCheckButton(prop, on_changed_cb, 'Login')

        prop = self.parent.get_property('contacts-list-header-visible-host')
        on_changed_cb = lambda visible: self.parent.cl.get_column(5).set_visible(visible)
        chk_host = GConfCheckButton(prop, on_changed_cb, 'Host')

        hbox = gtk.HBox(True, 10)
        hbox.show()
        hbox.pack_start(chk_name, False, False)
        hbox.pack_start(chk_group, False, False)
        hbox.pack_start(chk_version, False, False)
        hbox.pack_start(chk_login, False, False)
        hbox.pack_start(chk_host, False, False)

        self.add_page('Contacts List', [('Font', btn_cl_font), ('Color', btn_cl_color), ('Background', btn_cl_bgcolor), ('Header', hbox)])

        prop = self.parent.get_property('message-font')
        on_changed_cb = lambda desc: self.parent.txt_send.invoke('modify_font', desc)
        btn_msg_font = GConfFontButton(prop, on_changed_cb)

        prop = self.parent.get_property('message-color')
        on_changed_cb = lambda color: self.parent.txt_send.invoke('modify_text', gtk.STATE_NORMAL, color)
        btn_msg_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('message-bgcolor')
        on_changed_cb = lambda color: self.parent.txt_send.invoke('modify_base', gtk.STATE_NORMAL, color)
        btn_msg_bgcolor = GConfColorButton(prop, on_changed_cb)

        self.add_page('Message Editor', [('Font', btn_msg_font), ('Color', btn_msg_color), ('Background', btn_msg_bgcolor)])

class SendDlg(ConfigableDialog):
    def __init__(self, title):
        ConfigableDialog.__init__(self, title=title, key='send')
        self.set_size_request(600, 400)
        self.set_icon(icons.App.get_pixbuf('logo'))

        self.action_area.set_homogeneous(False)
        self.action_area.set_spacing(10)

        self.cl = ContactList(get_contacts_func = (lambda : ipmsg.get_contacts().values()), grouping = settings['grouping'])
        self.cl.show()

        self.txt_send = MultiEntry()
        self.txt_send.show()
        self.txt_send.invoke('set_editable', True)
        self.txt_send.invoke('drag_dest_set', gtk.DEST_DEFAULT_DROP, [('text/plain', 0, 82), ('image/*', 0, 83)], gtk.gdk.ACTION_COPY)

        hsep = gtk.HSeparator()
        hsep.show()

        chbox = gtk.HBox(False, 1)
        self.lbl_cnt = gtk.Label('Contacts: %s' % len(ipmsg.get_contacts()))
        self.lbl_cnt.show()

        self.btn_group = gtk.ToggleButton('')
        self.btn_group.show()
        self.btn_group.set_active(settings['grouping'])
        self.btn_group.set_relief(gtk.RELIEF_NONE)
        def set_group_image(active):
            self.btn_group.set_image(icons.Toolbar.get_image(active and 'group-off' or 'group-on', cache=False))
        set_group_image(self.btn_group.get_active())

        def on_group_toggled(widget, *args):
            settings['grouping'] = not settings['grouping']
            widget.set_active(settings['grouping'])
            set_group_image(widget.get_active())
            self.cl.toggle_grouping()
            if settings['grouping']:
                self.cl.get_column(2).set_visible(False)
            else:
                self.cl.get_column(2).set_visible(self.get_gconf('contacts-list-header-visible-group'))
        self.btn_group.connect('toggled', on_group_toggled)
        self.btn_group.set_tooltip_markup('Switch groupping mode')

        self.btn_refresh = gtk.Button('')
        self.btn_refresh.set_image(icons.Toolbar.get_image('refresh', cache=False))
        self.btn_refresh.set_relief(gtk.RELIEF_NONE)
        self.btn_refresh.set_property('can-focus', False)
        self.btn_refresh.set_tooltip_markup('Request for the latest contacts list')
        self.btn_refresh.show()
        self.btn_refresh.connect("enter", lambda w: w.set_relief(gtk.RELIEF_NORMAL))
        self.btn_refresh.connect("leave", lambda w: w.set_relief(gtk.RELIEF_NONE))

        chbox.pack_start(self.lbl_cnt, False, False, 5)
        chbox.pack_end(self.btn_group, False, False, 5)
        chbox.pack_end(self.btn_refresh, False, False, 2)
        chbox.show() 
        contact_box = gtk.VBox(False, 2)
        contact_box.pack_start(chbox, False, False, 2)
        contact_box.pack_end(self.cl, True, True, 0)
        contact_box.show()

        hbox = gtk.HBox(False, 1)
        self.btn_share = gtk.Button('Attachments: None')
        self.btn_share.set_tooltip_markup('Click or drag to attach files')
        self.btn_share.show()
        self.btn_share.set_relief(gtk.RELIEF_NONE)
        self.btn_share.set_image(icons.Toolbar.get_image('attachment', cache=False))
        self.btn_share.set_property('can-focus', False)
        self.btn_share.connect("enter", lambda w: w.set_relief(gtk.RELIEF_NORMAL))
        self.btn_share.connect("leave", lambda w: w.set_relief(gtk.RELIEF_NONE))
        hbox.pack_start(self.btn_share, True, True, 2)

        self.chk_webshare = gtk.CheckButton('Via HTTP')
        self.chk_webshare.set_tooltip_markup('Use http style share')
        self.chk_webshare.set_active(settings['default_webshare'])
        self.chk_webshare.show()
        hbox.pack_end(self.chk_webshare, False, False, 5)
        hbox.show()

        vbox = gtk.VBox(False, 1)
        vbox.pack_start(hbox, False, False, 2)
        vbox.pack_end(self.txt_send, True, True, 0)
        vbox.show()

        hpan = gtk.HPaned()
        hpan.show()
        hpan.pack1(contact_box, shrink=False)
        hpan.pack2(vbox, shrink=False)
 
        self.vbox.pack_start(hpan, True, True, 0)

        self.chk_seal = gtk.CheckButton('Seal')
        self.chk_seal.set_tooltip_markup('Seal message')
        self.chk_seal.show()
        self.action_area.pack_end(self.chk_seal, False, False, 0)

        self.chk_password = gtk.CheckButton('Password')
        self.chk_password.set_tooltip_markup('Require password')
        self.chk_password.set_active(False)
        self.chk_password.show()
        self.action_area.pack_end(self.chk_password, False, False, 0)

        def seal_toggled_cb(w, *args):
            self.chk_password.set_sensitive(w.get_active())
            if not w.get_active():
                self.chk_password.set_active(False)
        self.chk_seal.connect('toggled', seal_toggled_cb)
        self.chk_seal.set_active(True)
        self.chk_seal.set_active(settings['default_seal_msg'])

        self.btn_send = gtk.Button('Send')
        self.btn_send.show()
        self.action_area.pack_end(self.btn_send, False, False, 0)

        self. update_gconf()

    def update_gconf(self):
        font = self.get_gconf('contacts-list-font')
        if font:
            desc = pango.FontDescription(font)
            self.cl.modify_font(desc)
        color = self.get_gconf('contacts-list-color')
        if color:
            self.cl.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
        bgcolor = self.get_gconf('contacts-list-bgcolor')
        if bgcolor:
            self.cl.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(bgcolor))

        self.cl.get_column(1).set_visible(self.get_gconf('contacts-list-header-visible-name'))
        if settings['grouping']:
            self.cl.get_column(2).set_visible(False)
        else:
            self.cl.get_column(2).set_visible(self.get_gconf('contacts-list-header-visible-group'))
        self.cl.get_column(3).set_visible(self.get_gconf('contacts-list-header-visible-version'))
        self.cl.get_column(4).set_visible(self.get_gconf('contacts-list-header-visible-status'))
        self.cl.get_column(5).set_visible(self.get_gconf('contacts-list-header-visible-host'))

        font = self.get_gconf('message-font')
        if font:
            desc = pango.FontDescription(font)
            self.txt_send.invoke('modify_font', desc)
        color = self.get_gconf('message-color')
        if color:
            self.txt_send.invoke('modify_text', gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
        bgcolor = self.get_gconf('message-bgcolor')
        if bgcolor:
            self.txt_send.invoke('modify_base', gtk.STATE_NORMAL, gtk.gdk.color_parse(bgcolor))

    def init_gconf(self):
        self.add_gconf_property('contacts-list-font', '')
        self.add_gconf_property('contacts-list-color', gtk.gdk.Color(0, 0, 0).to_string())
        self.add_gconf_property('contacts-list-bgcolor', gtk.gdk.Color(65535, 65535, 65535).to_string())
        self.add_gconf_property('contacts-list-header-visible-name', True)
        self.add_gconf_property('contacts-list-header-visible-host', True)
        self.add_gconf_property('contacts-list-header-visible-group', True)
        self.add_gconf_property('contacts-list-header-visible-version', True)
        self.add_gconf_property('contacts-list-header-visible-status', True)
        self.add_gconf_property('message-font', '')
        self.add_gconf_property('message-color', gtk.gdk.Color(0, 0, 0).to_string())
        self.add_gconf_property('message-bgcolor', gtk.gdk.Color(65535, 65535, 65535).to_string())

    def show_settings(self):
        dlg = SendSettings(self.key, parent=self)
        dlg.run()

class SendDialog:
    def __init__(self, org_msg=None, text='', recv_win=None):
        title = 'Send'
        if org_msg:
            packet, contact = org_msg
            title = 'Reply to ' + contact.get_desc()
        self.dlg = SendDlg(title)

        self.attachments = Attachments(self)
        self.recv_win = recv_win

        if org_msg:
            self.dlg.cl.select_contacts(contact.addr)

        self.dlg.txt_send.set_text(text)
        self.dlg.txt_send.invoke('drag_dest_unset')
        self.dlg.lbl_cnt.set_label('Contacts: %s' % len(ipmsg.get_contacts()))

        self.refresh_sid = self.dlg.btn_refresh.connect("button_press_event", lambda w, e: ipmsg.refresh())
        self.dlg.btn_share.connect('button_press_event', self.show_shares)
        self.dlg.btn_send.connect("pressed", lambda w, *args: self.do_send())

        self.dlg.drag_dest_set(gtk.DEST_DEFAULT_DROP, [('text/plain', 0, 82), ('image/*', 0, 83)], gtk.gdk.ACTION_COPY)
        self.dlg.connect('drag_motion', self.attachments.file_motion_cb)
        self.dlg.connect('drag_drop', self.attachments.file_drop_cb)
        self.dlg.connect('drag_data_received', self.attachments.drag_data_received)
        if not org_msg:
            self.reload_contacts_sid = gobject.timeout_add(1000, self.do_get_contacts)
            self.dlg.connect('destroy', lambda w : gobject.source_remove(self.reload_contacts_sid))

        hotkey_send = util.get_keyvals(settings['hotkey_send'])
        if hotkey_send:
            masks, keyval = hotkey_send
            def key_press_cb(w, e, *args):
                if e.type != gtk.gdk.KEY_PRESS:
                    return
                if e.keyval == keyval and len(masks) == len([x for x in masks if e.state & x]):
                    self.do_send()
                    w.emit_stop_by_name('key_press_event')

            self.dlg.connect('key_press_event', key_press_cb)

    def do_get_contacts(self):
        contacts = ipmsg.get_contacts().values()
        self.dlg.lbl_cnt.set_label('Contacts: %s' % len(contacts))
        self.dlg.cl.reload(get_contacts_func = (lambda : contacts))
        return True

    def show_shares(self, widget, event):
        self.attachments.run_dialog()
        self.update_file_summary()

    def update_file_summary(self):
        share_files = self.attachments.get_all()
        if len(share_files) == 0:
            file_summary = 'Attachments: None'
            tooltip = 'Click or drag to attach files...'
        else:
            file_summary = 'Attachments : %s' % (len(share_files))
            tooltip = '\n'.join(map(os.path.basename, share_files))
        self.dlg.btn_share.set_label(file_summary)
        self.dlg.btn_share.set_tooltip_markup(tooltip)

    def do_send(self):
        msg = self.dlg.txt_send.get_text()
        """
        if len(msg) == 0 and not self.attachments.get_all():
            return
        """

        seal = self.dlg.chk_seal.get_active()
        password = seal and self.dlg.chk_password.get_active()
        webshare = self.dlg.chk_webshare.get_active()

        selected = self.dlg.cl.get_selected_contacts()
        if len(selected) == 0:
            return
        else:
            ipmsg.send(selected, msg, self.attachments.get_all(), multicast=(len(selected) > 1), seal=seal, password=password, webshare=webshare)

        self.dlg.destroy()
        if self.recv_win:
            self.recv_win.destroy()

    def show(self):
        self.dlg.show()
        self.dlg.txt_send.invoke('grab_focus')

