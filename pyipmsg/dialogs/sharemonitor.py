# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk, gobject
import logging, logging.config

from pyipmsg.dialogs.configable import ConfigableDialog

class ShareMonitor:
    __COLS = [('Id', False), \
              ('Time', True), \
              ('Files', True),
              ('Users', True), \
              ('Status', True), ]

    def __init__(self, get_share_status_func=(lambda :[]), remove_share_func=(lambda id:None)):
        dlg = ConfigableDialog(key='sharemonitor', title='Shared files')
        dlg.set_size_request(600, 400)

        att_list = self.make_share_list()
        att_list.show()

        dlg.vbox.pack_start(att_list, True, True, 5)

        self.get_share_status_func = get_share_status_func
        self.remove_share_func = remove_share_func

        btn = gtk.Button('Remove')
        btn.show()
        btn.connect('button_press_event', self.on_remove)
        dlg.action_area.pack_start(btn)

        btn = gtk.Button('Close')
        btn.connect('button_press_event', lambda w, e: dlg.hide())
        btn.show()
        dlg.action_area.pack_start(btn)

        self.dlg = dlg
        self.att_list = att_list

        self.reload_contacts_sid = gobject.timeout_add(1000, self.do_get_share_status)

        self.dlg.connect('delete_event', self.dlg.hide_on_delete)

    def show(self):
        self.dlg.present()

    def make_share_list(self):
        ts = gtk.ListStore(str, str, str, str, str)
        tv = gtk.TreeView(ts)

        for idx, (header, visible) in enumerate(self.__COLS):
            col = gtk.TreeViewColumn(header)
            tv.append_column(col)
            cell = gtk.CellRendererText()
            col.pack_start(cell, True)
            col.add_attribute(cell, 'text', idx)
            col.set_sort_column_id(idx)
            col.set_visible(visible)

        tv.set_search_column(2)
        tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        tv.set_reorderable(True)
        tv.set_headers_visible(True)
        tv.show()

        return tv

    def find_row(self, id):
        model = self.att_list.get_model()
        itr = model.get_iter_first()
        while itr:
            if model.get_value(itr, 0) == id:
                return itr
            itr = model.iter_next(itr)
        return None

    def do_get_share_status(self):
        from ipmsg import UploadStatus
        model = self.att_list.get_model()
        for id, ctime, fname, addrs, details in self.get_share_status_func():
            cnt_waiting =  len([addr for (addr, fname, status) in details if status == UploadStatus.STOP])
            cnt_uploading =  len([addr for (addr, fname, status) in details if status == UploadStatus.START])
            cnt_finished =  len([addr for (addr, fname, status) in details if status == UploadStatus.FINISH])
            cnt_error =  len([addr for (addr, fname, status) in details if status == UploadStatus.ERROR])
            status_str = '%s/%s/%s/%s' % (cnt_waiting, cnt_uploading, cnt_finished, cnt_error)
            itr = self.find_row(id)
            if itr:
                model.set(itr, 4, status_str)
            else:
                row = [id, ctime, fname, addrs, status_str]
                model.append(row)

        return True

    def on_remove(self, w, e, *args):
        sel = self.att_list.get_selection()
        if sel.count_selected_rows() == 0:
            return

        model, paths = sel.get_selected_rows()
        itrs = [model.get_iter(path) for path in paths]
        for itr in itrs:
            self.remove_share_func(model.get_value(itr, 0))
            model.remove(itr)

