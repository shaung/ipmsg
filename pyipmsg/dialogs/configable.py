# -*- coding: utf-8 -*-

import re
import gtk, gobject, pango

from pyipmsg.conf.settings import SettingsDialog, GConfProperty
from pyipmsg import icons

class LayoutProperty:
    __key = None
    get_value = lambda : None

    def __init__(self, path, key, default, get_value=None):
        self.__key = key
        self.get_value = get_value
        self.conf = GConfProperty(path, key, default)

    def is_changed(self):
        val_conf = self.conf.get()
        val_curr = self.get_value()
        return val_conf != val_curr

    def save(self):
        self.conf.set(self.get_value())

class ConfigableDialog(gtk.Dialog):
    __gtype_name__ = 'ConfigableDialog'
    __gsignals__ = {'config_activiated': (gobject.SIGNAL_RUN_LAST, None, (str, str, int))}

    key = None

    def __init__(self, key, **kws):
        gtk.Dialog.__init__(self, **kws)
        self.key = key

        self.__gconf_properties = {}
        self.__layout_properties = {}

        self._build()
        self.init_gconf()

    def init_gconf(self):
        pass

    def _build(self):
        hbox_settings = gtk.HBox(False, 0)
        hbox_settings.show()

        btn_settings = gtk.Button()
        btn_settings.show()
        btn_settings.set_relief(gtk.RELIEF_NONE)
        btn_settings.set_image(icons.Toolbar.get_image('settings', cache=False))
        btn_settings.set_property('can-focus', False)

        def on_mouse_over(widget):
            widget.set_relief(gtk.RELIEF_NORMAL)
            widget.set_image(icons.Toolbar.get_image('settings-hover', cache=False))
        def on_mouse_leave(widget):
            widget.set_relief(gtk.RELIEF_NONE)
            widget.set_image(icons.Toolbar.get_image('settings', cache=False))
        btn_settings.connect("enter", on_mouse_over)
        btn_settings.connect("leave", on_mouse_leave)
        btn_settings.connect("button_press_event", self.on_settings)

        btn_save_layout = gtk.Button()
        btn_save_layout.show()
        btn_save_layout.set_relief(gtk.RELIEF_NONE)
        btn_save_layout.set_image(icons.Toolbar.get_image('save-layout', cache=False))
        btn_save_layout.set_property('can-focus', False)
        btn_save_layout.set_visible(False)

        def on_mouse_over(widget):
            widget.set_relief(gtk.RELIEF_NORMAL)
            widget.set_image(icons.Toolbar.get_image('save-layout-hover', cache=False))
        def on_mouse_leave(widget):
            widget.set_relief(gtk.RELIEF_NONE)
            widget.set_image(icons.Toolbar.get_image('save-layout', cache=False))
        btn_save_layout.connect("enter", on_mouse_over)
        btn_save_layout.connect("leave", on_mouse_leave)
        btn_save_layout.connect("button_press_event", self.on_save_layout)
        self.btn_save_layout = btn_save_layout

        hbox_settings.pack_start(btn_settings, False, False, 0)
        hbox_settings.pack_start(btn_save_layout, False, False, 0)
 
        halign = gtk.Alignment(0, 1, 0, 0)
        halign.show()
        halign.add(hbox_settings)

        self.action_area.set_layout(gtk.BUTTONBOX_END)
        self.action_area.pack_end(halign, False, False, 0)
        self.action_area.set_child_secondary(halign, True)

        self.connect('configure-event', self.on_resize)
        self.connect('window-state-event', self.on_state_changed)

        def get_window_width():
            return self.get_size()[0]

        def get_window_height():
            return self.get_size()[1]

        self.maximized = False
        self.add_layout_property('window-width', get_window_width(), get_window_width)
        self.add_layout_property('window-height', get_window_height(), get_window_height)
        self.add_layout_property('window-maximized', self.maximized, lambda : self.maximized)

        if self.get_gconf_layout('window-maximized'):
            self.maximize()
        else:
            self.resize(self.get_gconf_layout('window-width'), self.get_gconf_layout('window-height'))

    def get_gconf_layout(self, key):
        return self.__layout_properties[key].conf.get()

    def on_settings(self, widget, event, *args):
        self.show_settings()

    def show_settings(self):
        pass

    def on_save_layout(self, widget, event, *args):
        for key, prop in self.__layout_properties.items():
            prop.save()
        changed = self.is_layout_changed()
        self.btn_save_layout.set_visible(changed)

    def on_resize(self, widget, event, *args):
        changed = self.is_layout_changed()
        self.btn_save_layout.set_visible(changed)

    def on_state_changed(self, widget, event, *args):
        self.maximized = event.new_window_state & gtk.gdk.WINDOW_STATE_MAXIMIZED

    def is_layout_changed(self):
        for key, prop in self.__layout_properties.items():
            if prop.is_changed():
                return True
        return False

    def add_layout_property(self, key, default, get_value):
        prop = LayoutProperty(self.key, key, default, get_value)
        self.__layout_properties[key] = prop

    def add_gconf_property(self, key, default):
        prop = GConfProperty(self.key, key, default)
        self.__gconf_properties[key] = prop

    def get_gconf(self, key):
        return self.__gconf_properties[key].get()

    def set_gconf(self, key, value):
        self.__gconf_properties[key].set(value)

    def get_property(self, key):
        return self.__gconf_properties[key]

    def get_all_properties(self):
        return self.__gconf_properties.keys()


gobject.type_register(ConfigableDialog)

if __name__ == '__main__':
    dlg = ConfigableDialog(key='test', title='simple test')
    dlg.run()
