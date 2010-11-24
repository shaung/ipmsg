# -*- coding: utf-8 -*-

import gtk, pango

class BaseMessageDialog(gtk.MessageDialog):
    pass

class ConfigValidationErrorDialog(BaseMessageDialog):
    def __init__(self, parent, errors, **kws):
        BaseMessageDialog.__init__(self, parent=parent, type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_CLOSE, **kws)
        self.set_title('Item validation error')
        pre = 'The settings cannot be saved due to the following errors. \n\n<b>%s</b>\n\n Please correct the errors and try again.'
        self.set_markup(pre % ': '.join(errors))
        self.connect('response', self.on_close)

    def on_close(self, w, id, *args):
        self.destroy()

class ResendConfimDialog(BaseMessageDialog):
    def __init__(self, parent, msg, **kws):
        BaseMessageDialog.__init__(self, parent=parent, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, **kws)
        self.set_title('Message delivery error')
        pre = 'The following message is not deliverd. \n\n%s\n\n <b>Would you like to give it a retry?</b>'
        self.set_markup(pre % msg)

class AttachmentsErrorDialog(BaseMessageDialog):
    def __init__(self, parent, errors, **kws):
        BaseMessageDialog.__init__(self, parent=parent, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, **kws)
        self.set_title('File attach error')
        pre = 'The following file can not sent. \n\n%s\n\n <b>Would you like to continue with other files?</b>'
        self.set_markup(pre % '\n'.join([':'.join(e) for e in errors]))

class NetworkErrorDialog(BaseMessageDialog):
    def __init__(self, parent, **kws):
        BaseMessageDialog.__init__(self, parent=parent, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, **kws)
        self.set_title('Network error')
        pre = '<b>Opps! I can\'t find any avalible network connection. Going offline.</b>'
        self.set_markup(pre)
        self.connect('response', self.on_close)

    def on_close(self, w, id, *args):
        self.destroy()

class AddressBindDialog(BaseMessageDialog):
    def __init__(self, parent, port, **kws):
        BaseMessageDialog.__init__(self, parent=parent, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK_CANCEL, **kws)
        self.set_title('Address binding error')
        pre = '<b>The port %s is already in use. </b>' % port
        self.set_markup(pre)
        adj = gtk.Adjustment(port+1, 1024, 65535, 1, 1, 0)
        self.new_port = gtk.SpinButton(adj, 0, 0)
        self.new_port.set_wrap(True)
        self.new_port.show()
        hbox = gtk.HBox()
        hbox.show()
        lbl = gtk.Label('Specify a new port:')
        lbl.show()
        hbox.pack_start(lbl)
        hbox.pack_start(self.new_port, True, True, 2)
        self.vbox.pack_end(hbox)
