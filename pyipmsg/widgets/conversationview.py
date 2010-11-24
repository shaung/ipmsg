# -*- coding: utf-8 -*-

import gtk, gobject, pango
import re
from textview import HyperMultiEntry

class ConversationView(HyperMultiEntry):
    __gtype_name__ = 'ConversationView'

    def __init__(self, rules, text=''):
        self.styles = {}
        self.styles['title-from'] = {
            'font-desc'            : None,
            'foreground'           : '#62a329c029c0',
            'paragraph-background' : '#C6B9A6',
            #'weight'               : pango.WEIGHT_BOLD,
            'justification'        : gtk.JUSTIFY_LEFT,
            'indent'               : 5,
            'pixels-above-lines'   : 6,
            'pixels-below-lines'   : 6,
            #'size_points'          : 10,
        }
        self.styles['title-to'] = {
            'font-desc'            : None,
            'foreground'           : '#111111',
            'paragraph-background' : '#FFB9A6',
            #'weight'               : pango.WEIGHT_BOLD,
            'justification'        : gtk.JUSTIFY_RIGHT,
            'indent'               : 5,
            'pixels-above-lines'   : 6,
            'pixels-below-lines'   : 6,
            #'size_points'          : 10,
        }
        self.styles['body-from'] = {
            'paragraph-background' : '#ffffff',
            'foreground' : 'black',
            'pixels-above-lines': 4,
            'justification': gtk.JUSTIFY_LEFT,
            'indent': 10,
            'size_points': 9,
        }
        self.styles['body-to'] = {
            'paragraph-background' : '#cccccc',
            'foreground' : 'black',
            'pixels-above-lines': 4,
            'justification': gtk.JUSTIFY_LEFT,
            'indent': 10,
            'size_points': 9,
        }
        self.styles['time-from'] = {
            'foreground' : '#333333',
            'paragraph-background' : self.styles['body-from']['paragraph-background'],
            'weight': pango.WEIGHT_BOLD,
            'style': pango.STYLE_ITALIC,
            'indent': 5,
            'size_points': 9,
            'justification': self.styles['title-from']['justification'],
        }
        self.styles['time-to'] = {
            'foreground' : '#333333',
            'paragraph-background' : self.styles['body-to']['paragraph-background'],
            'weight': pango.WEIGHT_BOLD,
            'style': pango.STYLE_ITALIC,
            'indent': 5,
            'size_points': 9,
            'justification': self.styles['title-to']['justification'],
        }
        self.styles['header_line'] = {
            'background' : 'darkgray',
            'paragraph-background' : '#000000',
            'size': 1,
        }
        self.styles['spacing'] = {
            'size' : 2000,
            'pixels-above-lines': 8,
            'paragraph-background' : '#ffffff',
        }
        self.styles['highlight'] = {
            'foreground' : 'black',
            'background' : '#ffef00',
            'weight': pango.WEIGHT_BOLD,
        }

        HyperMultiEntry.__init__(self, rules, text)

        self._textview.set_cursor_visible(False)

        self.clear()
        self.__highlight_tags = []

    def set_highlight(self, keyword):
        if keyword == self.keyword:
            return
        self.keyword = keyword
        
        buf = self._textview.get_buffer()
        for tag in self.__highlight_tags:
            buf.remove_tag(tag, buf.get_start_iter(), buf.get_end_iter())
        self.__all_tags['highlight'] = []

        # FIXME: position calculation incorrect when there are asian characters
        text = unicode(self.get_text(), 'utf8')
        for match in re.finditer(unicode(keyword, 'utf8'), text, re.U):
            for (start, length) in self.__all_tags['body-from'] + self.__all_tags['body-to']:
                if match.start(0) >= start and match.end(0) <= start + length:
                    break
            else:
                continue
            tag = buf.create_tag(None, **self.styles['highlight'])
            self.__highlight_tags.append(tag)
            url = match.group(0)
            buf.apply_tag(tag, buf.get_iter_at_offset(match.start(0)), buf.get_iter_at_offset(match.end(0)))
            self.__all_tags['highlight'].append((buf.get_char_count(), len(text)))

    def clear(self):
        self.history = []
        self._style_tags = {}
        self.__all_tags = {}
        buf = self._textview.get_buffer()
        for k, v in self.styles.items():
            self.__all_tags[k] = []
            tagtable = buf.get_tag_table()
            tag = tagtable.lookup(k)
            if tag:
                tagtable.remove(tag)
            self._style_tags[k] = buf.create_tag(k, **v)
        self.keyword = ''
 
        self.set_text('')

    def reload_styles(self):
        history = self.history[:]
        self.clear()
        for text, style in history:
            self._append_text(text, style)

    def _append_title(self, title):
        buf = self._textview.get_buffer()
        anchor = buf.create_child_anchor(buf.get_end_iter())
        vbox = gtk.VBox()
        item = gtk.MenuItem(title)
        item.select()
        item.show()
        vbox.pack_start(item, True, True)
        vbox.show()
        self._textview.add_child_at_anchor(vbox, anchor)

    def append_dummy(self):
        self._append_text(' ')

    def append_title(self, io, text):
        self._append_text(text + '\n', 'title-%s' % (io and 'from' or 'to'))

    def append_time(self, io, text):
        self._append_text(text, 'time-%s' % (io and 'from' or 'to'))

    def append_header_line(self):
        self._append_text('\n', 'header_line')

    def append_spacing(self):
        self._append_text('\n', 'spacing')

    def append_body(self, io, text):
        self._append_text(text, 'body-%s' % (io and 'from' or 'to'))

    def _append_text(self, text, style=None):
        self.history.append((text, style))
        buf = self._textview.get_buffer()
        itr = buf.get_end_iter()
        cur_endpos = buf.get_char_count()
        #cur_endpos = len(unicode(self.get_text(), 'utf8'))
        if style:
            self.__all_tags[style].append((cur_endpos, len(text)))
            buf.insert_with_tags_by_name(itr, text, style)
            if style[:4] == 'body':
                self.recognize_url(cur_endpos, cur_endpos + len(text))
        else:
            buf.insert(itr, text)

gobject.type_register(ConversationView)

