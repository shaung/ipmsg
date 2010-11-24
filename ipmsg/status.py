# -*- coding: utf-8 -*-

from ipmsg import consts as c
from ipmsg.message import engine
from ipmsg.config import settings
from ipmsg.share import upload_manager

from ipmsg.consts import STAT_TABLE, STAT_ON, STAT_AFK, STAT_INVISIBLE, STAT_OFF, STAT_NAME
__all__ = [ 'STAT_TABLE', 'STAT_ON', 'STAT_AFK', 'STAT_INVISIBLE', 'STAT_OFF', \
            'STAT_NAME', 'Status']

class Status:
    status = STAT_OFF
    msg = ''

    def __init__(self, stat=None):
        self.status = stat or STAT_OFF

    def is_on(self):
        return self.status == STAT_ON

    def is_afk(self):
        return self.status == STAT_AFK

    def is_invisible(self):
        return self.status == STAT_INVISIBLE

    def is_off(self):
        return self.status == STAT_OFF

    def get_status(self):
        return (self.status, self.msg)

    def get_name(self):
        return STAT_NAME[self.status]

    def switch_to(self, stat_tuple, force=True):
        new_stat, new_msg = stat_tuple

        if new_stat not in STAT_TABLE:
            return

        if self.status == new_stat:
            if force and self.status in (STAT_ON, STAT_AFK):
                engine.notify_status_all(is_afk=(self.status == STAT_AFK))
            return

        if new_stat != STAT_OFF:
            self.turn_on()

        if new_stat == STAT_AFK:
            if self.status == STAT_ON:
                engine.notify_status_all(is_afk=True)
            else:
                engine.helloall(is_afk=True)
        elif new_stat == STAT_ON:
            if self.status == STAT_AFK:
                engine.notify_status_all(is_afk=False)
            else:
                engine.helloall()
        elif new_stat == STAT_INVISIBLE:
            if self.status != STAT_OFF:
                engine.bye()
            else:
                engine.helloall(is_secret=True)
                engine.bye()
        elif new_stat == STAT_OFF:
            self.turn_off()

        self.status, self.msg = new_stat, new_msg

    def turn_on(self):
        #settings['stat_msg'] = [STAT_ON, '']
        #settings['auto_reply_msg'] = ''
        if self.status == STAT_OFF:
            engine.start_server()
            upload_manager.start_daemon(engine.get_addr())
        #self.update()

    def turn_off(self):
        if self.status == STAT_OFF:
            return
        if self.status != STAT_INVISIBLE:
            try:
                engine.bye()
            except:
                pass
        self.status = STAT_OFF
        engine.stop_server()
        upload_manager.stop_daemon()

    def update(self):
        self.switch_to(settings['stat_msg'])


status = Status()
