# -*- coding: utf-8 -*-

__all__ = ['config', 'consts', 'crypto', 'engine', 'message', 'history', 'contact', 'packet', 'share', 'status', 'util', ]

import os

basedir = os.path.expanduser('~/.ipmsg/')
for path in ('', 'rsa', 'webshare'):
    try:
        os.makedirs(os.path.join(basedir, path))
    except:
        pass


import util
from util import AttachmentError
import consts as c
import config
from message import engine, MessageHandler
from config import settings
import share
from share import DownloadManager, UploadManager, UploadStatus
from history import MessageLog
from status import status
from message.message import message_logger
from message.engine import NetworkError

_handler = MessageHandler()
_download_manager = DownloadManager()

def init(nics=[], port=c.IPMSG_DEFAULT_PORT, settings_file=None):
    #global engine
    engine.nics = dict(nics) or {'mock': '0.0.0.0'}
    engine.port = port
    if settings_file:
        config.load_settings(settings_file)
    message_logger.bind(config.settings['log_file_path'])

def rebind_log(self):
    message_logger.bind(settings['log_file_path'])

def turn_on():
    status.turn_on()
    engine.update_block_list()
    status.update()

def turn_off():
    try:
        status.turn_off()
    except:
        pass

def put_offline():
    try:
        status.turn_off()#.status = STAT_OFF
        #engine.stop_server()
        #share.upload_manager.stop_daemon()
    except:
        pass

def get_engine():
    global engine
    return engine

def resend(*msgs):
    return _handler.resend(*msgs)

def get_contacts():
    contacts = engine.get_contacts()
    rslt = {}
    for k, v in contacts.items():
        if v.has_left_for() < 5:
            rslt[k] = v
    return rslt

def get_status():
    return status

def update_status():
    return status.update()

def update_block_list():
    engine.update_block_list()

def get_block_list():
    return engine.block_ips

def refresh():
    engine.helloall()

def whatsnew():
    return _handler.proc_msg()

def start_download_all(atts, addr, save_dir=''):
    if not util.verify_dir(save_dir):
        # print 'can\'t create', save_dir
        return

    return _download_manager.start_new(atts, addr, save_dir)

def cancel_download(query_id):
    _download_manager.cancel(query_id)

def query_download_progress(query_id):
    return _download_manager.query_progress(query_id)

def verify_files(*files):
    return util.verify_files(*files)

def send(*args, **kws):
    _handler.send(*args, **kws)

def multicast(*args, **kws):
    _handler.send(*args, **kws)

def get_all_network_interface(nic=None):
    return util.get_nic_list(nic)

def get_share_status():
    return share.upload_manager.get_status()

def remove_share(sid):
    share.upload_manager.remove(sid)

def open_notice(*args):
    return _handler.open_notice(*args)

def read_notice(*args):
    return _handler.read_notice(*args)

def delete_notice(*args):
    return _handler.delete_notice(*args)


