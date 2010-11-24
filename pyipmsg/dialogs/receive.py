# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk, gobject, gnome, pango
import os, os.path, time, urllib, re
import logging, logging.config

import ipmsg
from ipmsg.config import settings
from ipmsg.share import Progress
from ipmsg.status import *

from pyipmsg.widgets import HyperMultiEntry
from pyipmsg import icons
from pyipmsg import util
from pyipmsg.dialogs.send import SendDialog
from pyipmsg.dialogs.configable import ConfigableDialog
from pyipmsg.conf.settings import SettingsDialog, GConfProperty
from pyipmsg.conf.widgets import GConfFontButton, GConfColorButton

class RecvSettings(SettingsDialog):
    def _build(self):
        SettingsDialog._build(self)

        prop = self.parent.get_property('header-font')
        on_changed_cb = lambda desc: self.parent.lbl_header.modify_font(desc)
        btn_header_font = GConfFontButton(prop, on_changed_cb)

        prop = self.parent.get_property('header-color')
        on_changed_cb = lambda color: self.parent.lbl_header.modify_text(gtk.STATE_NORMAL, color)
        btn_header_color = GConfColorButton(prop, on_changed_cb)

        self.add_page('Header', [('Font', btn_header_font), ('Color', btn_header_color)])

        prop = self.parent.get_property('content-font')
        on_changed_cb = lambda desc: self.parent.txt_recv.invoke('modify_font', desc)
        btn_content_font = GConfFontButton(prop, on_changed_cb)

        prop = self.parent.get_property('content-color')
        on_changed_cb = lambda color: self.parent.txt_recv.invoke('modify_text', gtk.STATE_NORMAL, color)
        btn_content_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('content-bgcolor')
        on_changed_cb = lambda color: self.parent.txt_recv.invoke('modify_base', gtk.STATE_NORMAL, color)
        btn_content_bgcolor = GConfColorButton(prop, on_changed_cb)

        self.add_page('Message', [('Font', btn_content_font), ('Color', btn_content_color), ('Background', btn_content_bgcolor)])

        prop = self.parent.get_property('link-color')
        def on_changed_cb(color):
            self.parent.txt_recv.link['foreground'] = color
            self.parent.txt_recv.recognize_url()
        btn_link_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('link-bgcolor')
        def on_changed_cb(color):
            self.parent.txt_recv.link['background'] = color
            self.parent.txt_recv.recognize_url()
        btn_link_bgcolor = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('link-hover-color')
        def on_changed_cb(color):
            self.parent.txt_recv.hover['foreground'] = color
            self.parent.txt_recv.recognize_url()
        btn_hover_color = GConfColorButton(prop, on_changed_cb)

        prop = self.parent.get_property('link-hover-bgcolor')
        def on_changed_cb(color):
            self.parent.txt_recv.hover['background'] = color
            self.parent.txt_recv.recognize_url()
        btn_hover_bgcolor = GConfColorButton(prop, on_changed_cb)

        self.add_page('Url', [('Color', btn_link_color), ('Background', btn_link_bgcolor),
                              ('Hover Color', btn_hover_color), ('Hover Background', btn_hover_bgcolor)])

class RecvDlg(ConfigableDialog):
    def __init__(self, title):
        ConfigableDialog.__init__(self, title=title, key='recv')
        self.set_size_request(600, 400)
        self.set_icon(icons.App.get_pixbuf('logo'))

        self.lbl_header = gtk.Label()
        self.lbl_header.show()
        hbox = gtk.HBox()
        hbox.show()
        self.img_status = gtk.Image()
        self.img_status.show()
        hbox.pack_start(self.img_status, False, False, 5)
        hbox.pack_start(self.lbl_header, True, True, 5)
        self.vbox.pack_start(hbox, False, False, 5)

        self.msg_area = gtk.VBox()
        self.msg_area.show()

        self.btn_att = gtk.Button()
        self.btn_att.show()
        self.hbox_att = gtk.HBox()
        img = icons.Toolbar.get_image('attachment')
        img.show()
        self.btn_att.set_image(img)
        self.hbox_att.pack_start(self.btn_att, True, True, 5)
        self.msg_area.pack_start(self.hbox_att, False, False, 0)

        self.txt_recv = HyperMultiEntry()

        self.txt_recv.invoke('set_editable', False)
        self.txt_recv.show()

        self.msg_area.pack_end(self.txt_recv, True, True, 1)
        self.vbox.pack_start(self.msg_area, True, True, 1)

        self.btn_open = gtk.Button('Click to open message')
        self.vbox.pack_end(self.btn_open, True, True, 1)

        self.btn_close = gtk.Button(label='Close')
        self.btn_close.connect("button_press_event", lambda w, e : self.destroy())
        self.btn_close.show()
        self.action_area.pack_start(self.btn_close, True, True, 0)

        self.btn_copy = gtk.Button(label='Copy')
        self.btn_copy.show()
        self.action_area.pack_start(self.btn_copy, True, True, 0)

        self.chk_refer = gtk.CheckButton('Quote')
        self.chk_refer.set_active(settings['default_quote_msg'])
        self.chk_refer.show()
        self.action_area.pack_start(self.chk_refer, True, True, 0)

        self.btn_reply = gtk.Button(label='Reply')
        self.btn_reply.show()
        self.action_area.pack_start(self.btn_reply, True, True, 0)

        self.update_gconf()

    def update_gconf(self):
        font = self.get_gconf('header-font')
        if font:
            desc = pango.FontDescription(font)
            self.lbl_header.modify_font(desc)
        color = self.get_gconf('header-color')
        if color:
            self.lbl_header.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))

        self.txt_recv.link['foreground'] = self.get_gconf('link-color')
        self.txt_recv.link['background'] = self.get_gconf('link-bgcolor')
        self.txt_recv.hover['foreground'] = self.get_gconf('link-hover-color')
        self.txt_recv.hover['background'] = self.get_gconf('link-hover-bgcolor')
        self.txt_recv.active['foreground'] = self.get_gconf('link-active-color')
        self.txt_recv.active['background'] = self.get_gconf('link-active-bgcolor')

        font = self.get_gconf('content-font')
        if font:
            desc = pango.FontDescription(font)
            self.txt_recv.invoke('modify_font', desc)
        color = self.get_gconf('content-color')
        if color:
            self.txt_recv.invoke('modify_text', gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
        bgcolor = self.get_gconf('content-bgcolor')
        if bgcolor:
            self.txt_recv.invoke('modify_base', gtk.STATE_NORMAL, gtk.gdk.color_parse(bgcolor))

    def init_gconf(self):
        self.add_gconf_property('header-font', '')
        self.add_gconf_property('header-color', gtk.gdk.Color(0, 0, 0).to_string())
        self.add_gconf_property('content-font', '')
        self.add_gconf_property('content-color', gtk.gdk.Color(0, 0, 0).to_string())
        self.add_gconf_property('content-bgcolor', gtk.gdk.Color(65535, 65535, 65535).to_string())
        self.add_gconf_property('link-color', 'blue')
        self.add_gconf_property('link-bgcolor', 'white')
        self.add_gconf_property('link-hover-color', 'red')
        self.add_gconf_property('link-hover-bgcolor', 'gray')
        self.add_gconf_property('link-active-color', 'red')
        self.add_gconf_property('link-active-bgcolor', 'gray')

    def show_settings(self):
        dlg = RecvSettings(self.key, parent=self)
        dlg.run()

class RecvDialog:
    def __init__(self, msg):
        self.msg = msg
        self.packet = msg.packet
        self.contact = msg.contact
        self.download_sid = None
        self.__gconf_key = 'recv/attachments'
        self.gconf_properties = {
            'last_save_folder_path' : GConfProperty(self.__gconf_key, 'last_save_folder_path', '.'),
        }

    def show(self):
        title = 'Received Message'
        dlg = RecvDlg(title=title)
        dlg.set_size_request(600, 400)

        dlg.lbl_header.set_text(self.contact.get_desc() + ' @ ' + time.ctime(self.msg.packet.timestamp))

        if self.msg.options['autoret']:
            msg_icon_name = 'msg-autoreply'
            dlg.img_status.set_from_file(icons.Window.get_path(msg_icon_name))
            dlg.img_status.set_tooltip_markup('Auto-reply')
        elif self.msg.options['multicast']:
            msg_icon_name = 'msg-multicast'
            dlg.img_status.set_from_file(icons.Window.get_path(msg_icon_name))
            dlg.img_status.set_tooltip_markup('Multi-cast')
        else:
            pass

        if self.msg.atts:
            filelist = ' '.join([f.name for f in self.msg.atts])
            dlg.btn_att.set_label(filelist)
            dlg.btn_att.set_tooltip_markup('\n'.join([f.name for f in self.msg.atts]))
            self.download_sid = dlg.btn_att.connect("button_press_event", self.do_download)
            dlg.hbox_att.show()

        dlg.txt_recv.set_text(self.msg.msg)

        def url_clicked_cb(widget, type, url, btn):
            if btn == 1:
                util.launch_file(url)
        dlg.txt_recv.connect('anchor-clicked', url_clicked_cb)

        if self.msg.options['seal']:
            def on_click_open(w, e):
                dlg.msg_area.set_visible(True)
                dlg.txt_recv.grab_focus()
                w.set_visible(False)
                ipmsg.open_notice(self.msg)
            dlg.btn_open.connect("button_press_event", on_click_open)
            dlg.btn_open.show()
            dlg.msg_area.set_visible(False)

        dlg.btn_copy.connect("button_press_event", lambda w, e : gtk.clipboard_get().set_text(self.msg.msg))

        press_id = dlg.btn_reply.connect("pressed", lambda w, *args: self.do_reply())

        self.dlg = dlg

        self.dlg.connect('destroy', self.on_destroy)

        hotkey_reply = util.get_keyvals(settings['hotkey_reply'])
        if hotkey_reply:
            masks, keyval = hotkey_reply
            def key_press_cb(w, e, *args):
                if e.type != gtk.gdk.KEY_PRESS:
                    return
                if e.keyval == keyval and len(masks) == len([x for x in masks if e.state & x]):
                    self.do_reply()
                    w.emit_stop_by_name('key_press_event')

            self.dlg.connect('key_press_event', key_press_cb)

        dlg.show()

    def on_destroy(self, w, *args):
        if self.dlg.btn_open.get_property('visible'):
            ipmsg.delete_notice(self.msg)

    def choose_save_dir(self):
        dlg = gtk.FileChooserDialog(title='Save', action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        # TODO: overwrite
        dlg.set_do_overwrite_confirmation(True)
        curr_folder = self.gconf_properties['last_save_folder_path']
        dlg.set_current_folder(curr_folder.get())

        rsps = dlg.run()
        if rsps == gtk.RESPONSE_OK:
            rslt = dlg.get_filename()
            curr_folder.set(os.path.abspath(rslt))
        else:
            rslt = None
        dlg.destroy()
        return rslt

    def do_download(self, widget, event):
        save_dir = self.choose_save_dir()
        self.save_dir = save_dir
        if not save_dir:
            return

        widget.set_label('Preparing...')
        self.start_download()

    def restart_download(self):
        self.cancel_download()
        self.start_download()

    def start_download(self):
        widget = self.dlg.btn_att
        self.query_id = ipmsg.start_download_all(self.msg.atts, self.msg.addr, self.save_dir)
        self.progress_sid = gobject.timeout_add(1000, self.do_download_progress, widget)
        widget.disconnect(self.download_sid)
        self.download_sid = widget.connect('button_press_event', self.do_confirm_download)

    def cancel_download(self):
        ipmsg.cancel_download(self.query_id)
        gobject.source_remove(self.progress_sid)

    def init_download(self):
        widget = self.dlg.btn_att
        filelist = ' '.join([f.name for f in self.msg.atts])
        widget.set_label(filelist)
        widget.disconnect(self.download_sid)
        self.download_sid = widget.connect("button_press_event", self.do_download)

    def do_confirm_download(self, widget, event):
        dlg = gtk.Dialog(title='', flags=gtk.DIALOG_MODAL)
        dlg.set_size_request(240, 100)
        lbl = gtk.Label('Download paused')
        lbl.show()
        dlg.vbox.pack_start(lbl, False, False, 5)

        hbox = gtk.HBox(True)
        hbox.show()

        def do_cancel_download(w, e, dlg):
            self.cancel_download()
            dlg.destroy()

        def do_restart_download(w, e):
            self.restart_download()
            dlg.destroy()

        btn = gtk.Button(label='Cancel')
        btn.connect('button_press_event', do_cancel_download, dlg)
        btn.show()
        hbox.pack_start(btn, True, True, 0)

        btn = gtk.Button(label='Restart')
        btn.connect('button_press_event', do_restart_download)
        btn.show()
        hbox.pack_start(btn, True, True, 0)

        btn = gtk.Button(label='Continue')
        btn.connect('button_press_event', lambda w, e : dlg.destroy())
        btn.show()
        hbox.pack_start(btn, True, True, 0)

        dlg.vbox.pack_start(hbox, True, True, 0)
        dlg.set_transient_for(self.dlg)
        dlg.show()
        dlg.run()

    def show_download_result(self):
        # TODO: open file
        dlg = gtk.Dialog(title='', flags=gtk.DIALOG_MODAL)
        dlg.set_size_request(240, 100)
        lbl = gtk.Label('Download completed')
        lbl.show()
        dlg.vbox.pack_start(lbl, False, False, 5)

        hbox = gtk.HBox(True)
        hbox.show()
        btn = gtk.Button(label='Open file')
        btn.show()
        def on_open_file(w, e, *args):
            util.launch_file(self.save_dir)
            dlg.destroy()
        btn.connect('button_press_event', on_open_file)
        if len(self.msg.atts) > 1:
            btn.set_sensitive(False)
        hbox.pack_start(btn, True, True, 0)

        btn = gtk.Button(label='Open dir')
        btn.show()
        def on_open_dir(w, e, *args):
            util.launch_file(self.save_dir)
            dlg.destroy()
        btn.connect('button_press_event', on_open_dir)
        hbox.pack_start(btn, True, True, 0)

        btn = gtk.Button(label='Close')
        btn.connect('button_press_event', lambda w, e : dlg.destroy())
        btn.show()
        hbox.pack_start(btn, True, True, 0)

        dlg.vbox.pack_start(hbox, True, True, 0)
        dlg.set_transient_for(self.dlg)
        dlg.show()
        dlg.run()

    def show_download_error(self):
        dlg = gtk.Dialog(title='', flags=gtk.DIALOG_MODAL)
        dlg.set_size_request(240, 100)
        lbl = gtk.Label('Error occured')
        lbl.show()
        dlg.vbox.pack_start(lbl, False, False, 5)

        hbox = gtk.HBox(True)
        hbox.show()
        btn = gtk.Button(label='Restart')
        btn.show()
        def on_restart(w, e, *args):
            self.restart_download()
            dlg.destroy()

        btn.connect('button_press_event', on_restart)
        if len(self.msg.atts) > 1:
            btn.set_sensitive(False)
        hbox.pack_start(btn, True, True, 0)

        def on_close(w, e):
            self.cancel_download()
            self.init_download()
            dlg.destroy()

        btn = gtk.Button(label='Close')
        btn.connect('button_press_event', on_close)
        btn.show()
        hbox.pack_start(btn, True, True, 0)

        dlg.vbox.pack_start(hbox, True, True, 0)
        dlg.set_transient_for(self.dlg)
        dlg.show()
        dlg.run()

    def do_download_progress(self, widget):
        progress = ipmsg.query_download_progress(self.query_id)

        curr_count = progress.curr_count
        curr_size = util.normalize_size(progress.curr_size)
        if progress.is_error():
            self.show_download_error()
            return False
        elif progress.is_done():
            # FIXME: speed caculation
            avg_speed = util.normalize_size(progress.avg_speed)
            progress_str = 'Done     : %s(%s) - %s/s' % (curr_count, curr_size, avg_speed)
            widget.disconnect(self.download_sid)
        elif progress.is_receiving():
            curr_speed = util.normalize_size(progress.curr_speed)
            progress_str = 'Receiving: %s(%s) - %s/s' % (curr_count, curr_size, curr_speed)
        else:
            progress_str = 'Preparing...'
        widget.set_label(progress_str)

        if progress.is_done():
            self.show_download_result()
            widget.hide()
            return False
        return True

    def do_reply(self):
        text = ''
        if self.dlg.chk_refer.get_active():
            quote_char = settings['quote_char']
            text = ''.join([quote_char + line + '\n' for line in self.msg.msg.split('\n')])

        if settings['keep_recv_window_when_reply']:
            recv_win = self.dlg
        else:
            recv_win = None
            self.dlg.emit('destroy')

        send_dlg = SendDialog((self.msg.packet, self.msg.contact), text, recv_win)
        send_dlg.show()

