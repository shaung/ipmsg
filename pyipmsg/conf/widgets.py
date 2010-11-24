# -*- coding: utf-8 -*-

import gtk, pango

class GConfWidgetMixin:
    def __init__(self, gconf_property, on_changed_cb):
        self.gconf_property = gconf_property
        self.on_changed_cb = on_changed_cb

    def get(self):
        return self.gconf_property.get()

    def set(self, value):
        self.gconf_property.set(value)

class GConfFontButton(gtk.FontButton, GConfWidgetMixin):
    def __init__(self, gconf_property, on_changed_cb):
        GConfWidgetMixin.__init__(self, gconf_property, on_changed_cb)
        gtk.FontButton.__init__(self)

        try:
            self.set_font_name(self.get())
        except:
            pass
        self.show()

        self.connect('font-set', self.on_font_selected)

    def on_font_selected(self, widget, *args):
        font = widget.get_font_name()
        desc = pango.FontDescription(widget.get_font_name())
        self.set(font)
        self.on_changed_cb(desc)

class GConfColorButton(gtk.ColorButton, GConfWidgetMixin):
    def __init__(self, gconf_property, on_changed_cb):
        GConfWidgetMixin.__init__(self, gconf_property, on_changed_cb)
        gtk.ColorButton.__init__(self)

        try:
            self.set_color(self.get())
        except:
            pass
        self.show()

        self.connect('color-set', self.on_color_selected)

    def get(self):
        return gtk.gdk.color_parse(GConfWidgetMixin.get(self))

    def on_color_selected(self, widget, *args):
        color = self.get_color()
        self.set(color.to_string())
        self.on_changed_cb(color)

class GConfCheckButton(gtk.CheckButton, GConfWidgetMixin):
    def __init__(self, gconf_property, on_changed_cb, label):
        GConfWidgetMixin.__init__(self, gconf_property, on_changed_cb)
        gtk.CheckButton.__init__(self, label)

        try:
            self.set_active(self.get())
        except:
            pass
        self.show()

        self.connect('toggled', self.on_toggled)

    def on_toggled(self, widget, *args):
        active = self.get_active()
        self.set(active)
        self.on_changed_cb(active)

