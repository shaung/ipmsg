# -*- coding: utf-8 -*-

import gtk, gobject, pango
import re

class MultiEntry(gtk.ScrolledWindow):
    def __init__(self, text=''):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_OUT)
        self._textview = gtk.TextView()
        self._textview.show()
        self._textview.set_wrap_mode(gtk.WRAP_CHAR)
        self.add(self._textview)
        self.set_text(text)

    def get_text(self):
        buf = self._textview.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter())

    def set_text(self, text):
        self._textview.get_buffer().set_text(text)

    def get_textview(self):
        return self._textview

    def invoke(self, funcname, *args):
        func = getattr(gtk.TextView, funcname)
        return func(self._textview, *args)

class HyperMultiEntry(MultiEntry):
    __gtype_name__ = 'MultiEntry'
    __gsignals__ = {'anchor-clicked': (gobject.SIGNAL_RUN_LAST, None, (str, str, int))}

    def __init__(self, rules={}, text=''):
        self.__tags = []
        self.link = { 'background' : 'white', 'foreground' : 'blue', }
        self.hover = { 'background' : 'gray', 'foreground' : 'red', }
        self.active = { 'background' : 'white', 'foreground' : 'red', }

        self.rules = {
            'http'  : 'http://[^\s\\n]+',
            'https' : 'https://[^\s\\n]+',
            'ftp'   : 'ftp://[^\s\\n]+',
        }
        self.rules.update(rules)

        MultiEntry.__init__(self, text)

        self.connect('motion-notify-event', self._motion)
        self.connect('focus-out-event', lambda w, e: self._textview.get_buffer().get_tag_table().foreach(self.__tag_reset, e.window))
        self.recognize_url()

    def set_text(self, text):
        MultiEntry.set_text(self, text)
        self.recognize_url()

    def recognize_url(self, startpos=0, endpos=0):
        buf = self._textview.get_buffer()
        if startpos > endpos:
            return
        start_itr = startpos and buf.get_iter_at_offset(startpos) or buf.get_start_iter()
        end_itr = endpos and buf.get_iter_at_offset(endpos) or buf.get_end_iter()

        for tag in self.__tags:
            buf.remove_tag(tag, start_itr, end_itr)
            self.__tags = [t for t in self.__tags if t != tag]

        text = buf.get_text(start_itr, end_itr)
        for name, exp in self.rules.items():
            while startpos < endpos:
                match = re.search(exp, text, re.U)
                if match is None:
                    break
                url = match.group(0)
                tag = buf.create_tag(None, **self.link)
                tag.set_data('url', url)
                tag.connect('event', self._tag_event, name, url)
                self.__tags.append(tag)
                start = buf.get_iter_at_offset(startpos + match.start())
                end = buf.get_iter_at_offset(startpos + match.end())
                buf.apply_tag(tag, start, end)

                text = text[match.end():]
                startpos += match.end()

    def _tag_event(self, tag, view, ev, _iter, text, anchor):
        _type = ev.type
        if _type == gtk.gdk.MOTION_NOTIFY:
            return
        elif _type in [gtk.gdk.BUTTON_PRESS, gtk.gdk.BUTTON_RELEASE]:
            button = ev.button
            cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
            if _type == gtk.gdk.BUTTON_RELEASE:
                self.emit('anchor-clicked', text, anchor, button)
                self.__set_anchor(ev.window, tag, cursor, self.hover)
            elif button in [1, 2]:
                self.__set_anchor(ev.window, tag, cursor, self.active)

    def _motion(self, view, event):
        window = event.window
        x, y, _ = window.get_pointer()
        x, y = self._textview.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        tags = self._textview.get_iter_at_location(x, y).get_tags()
        for tag in tags:
            if tag.get_data('url'):
                for t in set(self.__tags) - set([tag]):
                    self.__tag_reset(t, window)
                self.__set_anchor(window, tag, gtk.gdk.Cursor(gtk.gdk.HAND2), self.hover)
                break
        else:
            tag_table = self._textview.get_buffer().get_tag_table()
            tag_table.foreach(self.__tag_reset, window)

    def __tag_reset(self, tag, window):
        if tag.get_data('url'):
            self.__set_anchor(window, tag, None, self.link)

    def __set_anchor(self, window, tag, cursor, prop):
        window.set_cursor(cursor)
        for key, val in prop.iteritems():
            tag.set_property(key, val)

gobject.type_register(HyperMultiEntry)

if __name__ == '__main__':
    dlg = gtk.Dialog()
    dlg.show()
    rules = {}
    rules['http'] = 'http://[^\s\\n]+'
    t = HyperMultiEntry(rules, 'hello')
    t.set_text('hello from http://google.com\nhaha')
    t.show()
    t.invoke('set_sensitive', True)
    t.invoke('modify_base', gtk.STATE_NORMAL, gtk.gdk.color_parse('#CCCCCC'))
    def clicked_cb(widget, type, url, btn):
        print widget, type, url, btn
        
    t.connect('anchor-clicked', clicked_cb)
    dlg.vbox.pack_start(t)
    dlg.run()
