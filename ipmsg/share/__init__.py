# -*- coding: utf-8 -*-

import os, os.path, time, logging
from multiprocessing import Process, Manager

from download import Progress, FileDownloader, DownloadError
from upload import FileServerHandler, ForkedTCPServer, UploadStatus
from http import WebShareServer
from ipmsg.message import engine
from ipmsg import consts as c
from ipmsg.util import *

log_download = logging.getLogger('DownloadManager')
log_upload = logging.getLogger('UploadManager')
log_http = logging.getLogger('HttpShare')

class DownloadManager:
    download_status = {}
    mngr = Manager()

    def start_new(self, atts, addr, save_dir):
        query_id = time.time()
        dl_entry = self.mngr.dict({})
        filedown = FileDownloader(dl_entry, addr)
        proc = Process(target = filedown.download, args=(atts, save_dir))
        proc.daemon = True
        self.download_status[query_id] = (dl_entry, proc)
        proc.start()
        return query_id

    def cancel(self, query_id):
        log_download.debug('canceled:%s' % query_id)
        dl_entry, proc = self.download_status[query_id]
        proc.terminate()

    def query_progress(self, query_id):
        if query_id not in self.download_status.keys() or self.download_status[query_id] == {}: 
            return None
        return self.download_status[query_id][0].values()[0]

class UploadServer(ForkedTCPServer):
    allow_reuse_address = True

    def __init__(self, addr, share_list, upload_status):
        ForkedTCPServer.__init__(self, addr, FileServerHandler, share_list, upload_status)

class UploadManager:
    mngr = Manager()
    share_list = mngr.list([])

    def __init__(self, addr=('', engine.port)):
        # FIXME: port
        #self.addr = addr
        self.proc = None
        self.upload_server = None
        self.upload_status = self.mngr.dict({})

    def start_daemon(self, addr):
        if self.proc:
            log_upload.debug('server already started: %s' % self.proc.pid)
            return
        self.upload_server = UploadServer(addr, self.share_list, self.upload_status)
        self.proc = Process(target=self.upload_server.serve_forever)
        self.proc.daemon = True
        self.proc.start()
        log_upload.debug('server started: %s. listening at %s' % (self.proc.pid, addr[1]))

    def stop_daemon(self):
        if not self.proc:
            log_upload.debug('server not started')
            return
        self.upload_server.server_close()
        self.proc.terminate()
        self.proc = None
        self.upload_server = None
        log_upload.debug('server stopped')

    def append_files(self, addr, paths):
        sid = str(time.time())
        rslt = []
        for path in paths:
            fid = len(self.share_list)
            self.share_list.append((fid, path, addr, sid))
            self.upload_status[fid] = UploadStatus.STOP
            rslt.append((fid, path))

        return self.get_message(rslt)

    def get_message(self, files):
        msg = u''
        for fid, path in files:
            msg += self.gen_file_info(fid, path)

        return msg

    def gen_file_info(self, fid, fname):
        size = long(os.path.getsize(fname))
        mtime = long(os.path.getmtime(fname))
        ftype = os.path.isfile(fname) and c.IPMSG_FILE_REGULAR or c.IPMSG_FILE_DIR
        return '%s:%s:%s:%s:%s:\x07' % (shex(fid), os.path.basename(fname), shex(size), shex(mtime), shex(ftype))

    # FIXME: upload progress
    def get_status(self):
        status_list = []
        sids = list(set(sid for (fid, fname, addr, sid) in self.share_list))
        for idx, the_sid in enumerate(sids):
            file_li = [args for args in self.share_list if args[-1] == the_sid]
            fnames = ','.join(os.path.basename(fname) for (fid, fname, addr, sid) in file_li)
            addrs = ','.join(addr[0] for (fid, fname, addr, sid) in file_li)
            details = []
            for (fid, fname, addr, sid) in file_li:
                details.append((addr, os.path.basename(fname), self.upload_status[fid]))
            status_list.append((the_sid, time.ctime(float(the_sid)), fnames, addrs, details))
        return status_list

    def remove(self, sid):
        for args in [args for args in self.share_list if args[-1] == sid]:
            self.share_list.remove(args)

upload_manager = UploadManager()
webshare_manager = WebShareServer(path='/tmp/ipmsg/webshare')
