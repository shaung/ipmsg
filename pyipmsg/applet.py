#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')
import gtk, gobject, gnome, gnomeapplet
import sys, os, os.path, subprocess, time, copy, socket
import urllib, re
import logging, logging.config

log = logging.getLogger('Applet')

import ipmsg
from ipmsg.status import *
from ipmsg.config import settings

from pyipmsg import notify
from pyipmsg import icons
from pyipmsg.dialogs import *
from pyipmsg.common import *
from pyipmsg import util

config_file = CONF_PATH
FACTORY_IID = 'OAFIID:GNOME_Panel_Pyipmsg_Factory'

gtk.rc_parse_string("""
style "pyipmsg"
{
    GtkMenuBar::shadow-type = none
    GtkMenuBar::internal-padding = 0
    GtkWidget::focus-line-width = 0
    GtkWidget::focus-padding = 0
}
style "pyipmsg-menubar"
{
    GtkMenuItem::toggle-spacing = 0
    GtkMenuItem::horizontal-padding = 0
    GtkMenuItem::width-chars = 0
    GtkMenuBar::shadow-type = none
    GtkMenuBar::internal-padding = 0
    GtkWidget::focus-line-width = 0
    GtkWidget::focus-padding = 0
}
style "pyipmsg-menuitem"
{
    GtkMenuItem::toggle-spacing = 0
    GtkMenuItem::horizontal-padding = 0
    GtkMenuItem::width-chars = 0
    GtkMenuBar::shadow-type = none
    GtkMenuBar::internal-padding = 0
    GtkWidget::focus-line-width = 0
    GtkWidget::focus-padding = 0
}
widget "*.pyipmsgapplet" style "pyipmsg"
widget "*.pyipmsgmenubar" style "pyipmsg-menubar"
widget "*.pyipmsgmenuitem" style "pyipmsg-menuitem"
""")

class Gui:
    def __init__(self, applet, iid):
        gnome.init(APPNAME, VERSION)
        self.applet = applet
        self.applet.set_name('pyipmsgapplet')
        self.applet.set_applet_flags(gnomeapplet.EXPAND_MINOR)
        self.applet.connect('change-orient', self.on_change_orient)

        self.incoming = []

        self.logviewer = LogViewer()
        self.pref = Preferences()
        self.share_monitor = ShareMonitor(ipmsg.get_share_status, ipmsg.remove_share)

        #self.clean_webshare()

        nics = ipmsg.get_all_network_interface()
        ipmsg.init(nics=nics, settings_file=config_file)
        gobject.timeout_add(100, self.mainloop)
        if nics:
            self.turn_on()

        self._build_ui()
        self._key_bind()

    def get_unread_msg_count(self):
        return len([m for m in self.incoming if not m.is_read()])

    def get_unread_att_count(self):
        return len([m for m in self.incoming if not m.is_read() and len(m.atts) > 0])

    def clean_webshare(self):
        # FIXME: it's convenient to remove the files programmatically but somehow dangerous 
        assert(WEB_SHARE_DIR.startswith(os.path.expanduser('~/.pyipmsg/')))
        for root, dirs, files in os.walk(WEB_SHARE_DIR, topdown=False):
            try:
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            except OSError:
                pass

    def turn_on(self):
        try:
            ipmsg.turn_on()
        except ipmsg.NetworkError:
            dlg = AddressBindDialog(None, ipmsg.get_engine().port)
            def on_resend_rsps(w, id, *args):
                dlg.destroy()
                if id == gtk.RESPONSE_OK:
                    ipmsg.get_engine().port = int(w.new_port.get_value())
                    self.turn_on()
                else:
                    sys.exit()
            dlg.connect('response', on_resend_rsps)
            dlg.show()

    def _build_ui(self):
        self.create_applet_menu()
        self.left_menu = self.create_left_menu()
        self.left_menu.set_border_width(0)
        sub = gtk.ImageMenuItem(gtk.STOCK_HELP)
        sub.set_image(icons.App.get_image('normal'))
        sub.get_child().set_label('')
        sub.set_submenu(self.left_menu)
        sub.show()
        self.menuitem = sub
        self.menuitem.set_border_width(0)
        self.menuitem.set_name('pyipmsgmenuitem')

        self.menubar.append(self.menuitem)
        self.menubar.set_border_width(0)
        self.menubar.connect("button_press_event", self.show_menu)
        self.menuitem.set_has_tooltip(True)
        self.menuitem.connect("query_tooltip", self.on_query_tooltip)

        self.box = gtk.VBox()
        self.box.show()
        self.box.pack_start(self.menubar, False, False, 0)
        self.applet.add(self.box)
        self.applet.set_property('can-focus', False)
        self.applet.show_all()
        self.applet.set_border_width(0)
        self.applet.connect("destroy", self.cleanup)

    def _key_bind(self):
        try:
            import keybinder
        except:
            #print 'you need the python-keybinder to enable the global hotkey'
            pass
        else:
            def on_cancel(w, *args):
                self.menuitem.deselect()
                self.menubar.deselect()
                self.menubar.grab_remove()
                gtk.gdk.keyboard_ungrab()
                gtk.gdk.pointer_ungrab()

            # FIXME: The menu selection works but somehow weird. I'm not sure i'm doing it right.
            def show_menu_cb():
                self.menubar.connect('cancel', on_cancel)
                self.menubar.connect('selection-done', on_cancel)
                self.menuitem.select()
                self.menubar.select_first(False)
                self.menuitem.activate()

            keybinder.bind('<Super>I', show_menu_cb)

    def cleanup(self, applet):
        self.applet.hide()
        notify.clean()
        gtk.main_quit()

    def create_menu(self, menuitems, parent=None):
        menu = gtk.Menu()
        if parent:
            sub = gtk.MenuItem(parent, True)
            sub.set_submenu(menu)
            sub.show()

        for menu_item in menuitems:
            if menu_item:
                if menu_item[1]:
                    item = gtk.ImageMenuItem(gtk.STOCK_HELP)
                    item.set_image(menu_item[1])
                    item.get_child().set_label(menu_item[0])
                else:
                    item = gtk.MenuItem(menu_item[0], False)
                item.set_sensitive(menu_item[2])
                item.connect('activate', *menu_item[3:])
            else:
                item = gtk.SeparatorMenuItem()
            item.show()
            menu.add(item)

        return parent and sub or menu

    def create_left_menu(self):
        menuitems = []
        menuitems.append(["Send", None, not ipmsg.get_status().is_off(), self.on_show_send_window])

        menuitems.append(None)

        for k, v in STAT_NAME.items():
            menuitems.append([v.title(), icons.Menu.get_status_image(k, cache=False), True, self.do_change_status_to, (k, '', '')])

        menuitems.append(None)

        stat_menuitems = []
        for (stat, stat_msg, autoreply_msg) in settings['status_list']:
            stat_menuitems.append([stat_msg.replace('_', '__'), icons.Menu.get_status_image(stat, cache=False), True, \
                self.do_change_status_to, (stat, stat_msg, autoreply_msg)])

        stat_menu = self.create_menu(stat_menuitems, 'More')

        menu = self.create_menu(menuitems)
        menu.append(stat_menu)
        return menu

    def show_menu(self, widget, event):
        if event.type != gtk.gdk.BUTTON_PRESS:
            return False
        if event.button != 1:
            widget.emit_stop_by_name("button_press_event")
        return False

    def do_change_status_to(self, widget, (new_stat, stat_msg, autoreply_msg)):
        try:
            if new_stat != STAT_OFF:
                settings['stat_msg'] = [new_stat, stat_msg]
                settings.save()
                ipmsg.update_status()
            else:
                ipmsg.turn_off()
        except ipmsg.NetworkError:
            ipmsg.put_offline()
            dlg = NetworkErrorDialog(None)
            dlg.show()
            dlg.run()

    def create_applet_menu(self):
        # TODO: icon, accelarator
        propxml="""
                <popup name="button3">
                <menuitem name="_Share_Monitor" verb="Share Monitor" label="_Share_Monitor"/>
                <menuitem name="_View_Log" verb="View Log" label="_View_Log"/>
                <menuitem name="_Preferences" verb="Preferences" label="_Preferences" pixtype="stock" pixname="gtk-preferences"/>
                <menuitem name="_About" verb="About" label="_About" pixtype="stock" pixname="gtk-about"/>
                </popup>"""
        verbs = [ ('Share Monitor', self.on_show_share_monitor), \
                  ('View Log', self.on_view_log), \
                  ('Preferences', self.on_show_preferences), \
                  ("About", self.on_show_about),]
        self.menubar = gtk.MenuBar()
        self.menubar.show()
        self.menubar.set_name('pyipmsgmenubar')
        self.applet.setup_menu(propxml, verbs, self.menubar)

    def on_show_preferences(self, *args, **kws):
        settings['group_list'] = list(set([contact.group for contact in ipmsg.get_contacts().values()]))
        def on_save_cb():
            ipmsg.update_block_list()
            ipmsg.update_status()
            ipmsg.rebind_log(settings['log_file_path'])
            settings['group_list'] = []
            settings.save()
        self.pref.show(on_save_cb)

    def on_show_share_monitor(self, *args, **kws):
        self.share_monitor.show()

    def on_show_about(self, *args, **kws):
        dlg = gtk.AboutDialog()
        dlg.set_name(APPNAME)
        dlg.set_program_name(APPNAME)
        dlg.set_version(VERSION)
        dlg.set_comments(APPDESC)
        dlg.set_website(URL)
        dlg.set_website_label(URL)
        dlg.set_authors(['%s<%s>' % (AUTHOR, EMAIL)])
        dlg.set_copyright('%s<%s>' % (AUTHOR, EMAIL))
        dlg.set_license(LICENSE_DESC)
        dlg.set_wrap_license(True)
        dlg.show_all()
        dlg.run()
        dlg.destroy()

    def on_show_send_window(self, widget):
        send_dlg = SendDialog()
        send_dlg.show()

    def on_view_log(self, *args, **kws):
        self.logviewer.show()

    def on_read_msg(self, widget, msg):
        ipmsg.read_notice(msg)
        recv_dlg = RecvDialog(msg)
        recv_dlg.show()
        self.update_icon()
        self.left_menu.remove(widget)

    def mainloop(self):
        try:
            messages, events = ipmsg.whatsnew()
            new_incoming = [m for m in messages if m.io == 1 and m not in self.incoming]
            paused = [m for m in messages if m.io == 0 and m.is_send_error()]
            read_notify = [m for m in messages if m.io == 0 and m.is_opened()]
            deleted_notify = [m for m in messages if m.io == 0 and m.is_ignored()]
        except ipmsg.NetworkError:
            ipmsg.put_offline()
            dlg = NetworkErrorDialog(None)
            dlg.show()
            dlg.run()
            return True

        if settings['enable_notify']:
            if settings['notify_online']:
                msg = ''.join([contact.get_desc() + ' signed online.\n' for contact in events if contact.status in (STAT_ON, STAT_AFK)])
                if len(msg) > 0:
                    notify.balloon('notify', msg, notify.EVENT)
            if settings['notify_offline']:
                msg = ''.join([contact.get_desc() + ' signed out.\n' for contact in events if contact.status == STAT_OFF])
                if len(msg) > 0:
                    notify.balloon('notify', msg, notify.EVENT)

            for msg in read_notify:
                notify.balloon('notify', '%s has opened your message.' % msg.contact.name , notify.EVENT)

            for msg in deleted_notify:
                notify.balloon('notify', '%s ignored your message.' % msg.contact.name , notify.EVENT)

        if settings['enable_notify'] and (not ipmsg.get_status().is_afk() or not settings['disable_notify_afk']):
            for msg in new_incoming:
                icon = msg.atts and notify.ATT or notify.MSG
                notify.balloon(msg.contact.get_desc(), msg.options['seal'] and '--Secret Message--' or msg.msg, icon)

        if settings['enable_popup'] and (not ipmsg.get_status().is_afk() or not settings['non_popup_when_afk']):
            for msg in new_incoming:
                recv_dlg = RecvDialog(msg)
                recv_dlg.show()
                ipmsg.read_notice(msg)
            new_incoming = []

        prev_unread = [m for m in self.incoming if not m.is_read()]
        self.incoming = [m for m in messages if m.io == 1]
        self.update_icon()

        for msg in [m for m in paused if m not in self.prev_paused]:
            if settings['notify_error']:
                notify.balloon('Error', 'Message not delivered', notify.EVENT)
            dlg = ResendConfimDialog(None, msg.msg)
            def on_resend_rsps(w, id, msg):
                if id == gtk.RESPONSE_YES:
                    ipmsg.resend(msg)
                w.destroy()
            dlg.connect('response', on_resend_rsps, msg)
            dlg.show()

        self.prev_paused = paused[:]

        for msg in new_incoming:
            label = '    %s ... (%s ago)' % (msg.contact.get_desc(), util.calc_time(msg.packet.age()))
            item = gtk.MenuItem(label, False)
            item.connect('activate', self.on_read_msg, msg)
            item.show()
            self.left_menu.insert(item, 1)
        self.left_menu.get_children()[0].set_sensitive(not ipmsg.get_status().is_off())

        return True

    def update_icon(self):
        msg_count = self.get_unread_msg_count()
        att_count = self.get_unread_att_count()
        if msg_count == 0:
            self.menuitem.set_image(icons.App.get_image('normal'))
        elif att_count == 0:
            self.menuitem.set_image(icons.App.get_image('message'))
        else:
            self.menuitem.set_image(icons.App.get_image('attachment'))

    def on_query_tooltip(self, widget, x, y, kb_mode, tooltip, *args):
        status_name = ipmsg.get_status().get_name().title()
        contacts = ipmsg.get_contacts()
        engine = ipmsg.get_engine()
        desc = '<b>%s</b>\n%s@%s:%s\n%s contacts' % (status_name, engine.login, engine.host, engine.port, len(contacts))
        tooltip.set_markup(desc)
        tooltip.set_icon(icons.App.get_status_pixbuf(ipmsg.get_status().status))
        return True

    def on_change_orient(self, w, orient, *args):
        if orient in (gnomeapplet.ORIENT_UP, gnomeapplet.ORIENT_DOWN):
            self.menubar.set_pack_direction(gtk.PACK_DIRECTION_LTR)
        elif orient in (gnomeapplet.ORIENT_LEFT, gnomeapplet.ORIENT_RIGHT):
            self.menubar.set_pack_direction(gtk.PACK_DIRECTION_TTB)

def factory(applet, iid):
    applet.set_background_widget(applet)
    Gui(applet, iid)
    return gtk.TRUE

def debug():
    gtk.settings_get_default().set_long_property('gtk-button-images', True, 'True')
    mainWindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
    mainWindow.set_title(APPNAME)
    mainWindow.connect("destroy", quit)

    applet = gnomeapplet.Applet()
    gui = Gui(applet, None)
    applet.reparent(mainWindow)

    mainWindow.show_all()

    gtk.main()
    sys.exit()

def main():
    log.debug('starting factory')
    gtk.settings_get_default().set_long_property('gtk-button-images', True, 'True')
    gnomeapplet.bonobo_factory(FACTORY_IID, gnomeapplet.Applet.__gtype__, APPNAME, VERSION, factory)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == "debug":
            debug()
        else:
            print 'usage: applet.py debug'

