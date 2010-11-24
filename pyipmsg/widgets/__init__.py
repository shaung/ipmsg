# -*- coding: utf-8 -*-

import gtk, gobject, pango
import re
from textview import MultiEntry, HyperMultiEntry
from conversationview import ConversationView

class CellRendererImageButton(gtk.CellRendererPixbuf):
    __gsignals__ = {
        'clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
    }

    def __init__(self):
        gtk.CellRendererPixbuf.__init__(self)
        self.set_property('mode',gtk.CELL_RENDERER_MODE_ACTIVATABLE)

    def do_activate(self, event, widget, path, background_area, cell_area, flags):
        self.emit('clicked', path)

gobject.type_register(CellRendererImageButton)

