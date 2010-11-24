# -*- coding: utf-8 -*-

import socket, re, sys, os, os.path, logging
import time, mmap, io
import SocketServer

from ipmsg import consts as c
from ipmsg.config import settings
from ipmsg.util import *

MIN_MMAP_SIZE = 0 # always use mmap
#MIN_MMAP_SIZE = 0x4000 # use mmap for file over 16kb
MIN_BUF_SIZE = 0x100000 # 1mb
DEF_BUF_SIZE = 0x400000 # 4mb
MMAP_BLOCK_SIZE = 0x4000000 # 40mb

log = logging.getLogger('Upload')

class FileType:
    FILE, DIR, RET, UNKNOWN = range(4)

class UploadError(Exception):
    pass

class FileServerHandler(SocketServer.BaseRequestHandler):
    get_shared_file_info = None

    def handle(self):
        try:
            self._buffer = mmap.mmap(-1, DEF_BUF_SIZE)
            data = self.request.recv(524288)
            addr = self.request.getpeername()

            what, finfo = self.get_file_info(data)
            self.what = what
            if what == FileType.FILE:
                ref_cntr, req_fid, offset = finfo
                self.qid = self.server.register(addr, int(req_fid, 16))
                self.send_file(finfo, addr)
            elif what == FileType.DIR:
                ref_cntr, req_fid = finfo
                self.qid = self.server.register(addr, int(req_fid, 16))
                self.send_dir(finfo, addr)
        except Exception as e:
            self.server.notify_error(self.qid)
            log.debug('Error: %s' % e)
        else:
            self.server.notify_finish(self.qid)
        finally:
            self._buffer.close()
            self.request.close()

    def send_file(self, finfo, addr):
        ref_cntr, req_fid, offset = finfo
        li = self.server.get_fileinfo(int(req_fid, 16), addr)
        if len(li) == 0:
            raise UploadError, 'file doesn\'t exist %s' % req_fid

        for (fid, fpath, (ip, port), status) in li:
            self.send_file_data(fpath)

        self.flush()

    def send_dir(self, finfo, addr):
        ref_cntr, req_fid = finfo
        li = self.server.get_fileinfo(int(req_fid, 16), addr)
        if len(li) == 0:
            raise UploadError, 'folder not exist %s' % req_fid

        for (fid, fpath, (ip, port), status) in li:
            for what, path in self.walk(fpath):
                if what == FileType.FILE:
                    self.send_file_data(path)
                else:
                    header = self.gen_header(what, path)
                    self.buffer(header)
            self.flush()

    def buffer(self, data):
        pos = self._buffer.tell()
        new_pos = pos + len(data)
        self._buffer[pos : new_pos] = data
        self._buffer.seek(new_pos)

    def flush(self):
        sz = self._buffer.tell()
        if sz > 0:
            self.request.sendall(self._buffer[:sz])
            self._buffer.seek(0)

    def walk(self, fpath):
        get_sz = lambda x : os.path.getsize(os.path.join(fpath, x))
        yield FileType.DIR, fpath
        names = os.listdir(fpath)
        names.sort(cmp = lambda x, y: get_sz(x) <= get_sz(y))
        for nm in names:
            f = os.path.join(fpath, nm)
            if os.path.isdir(f):
                for x in self.walk(f):
                    yield x
            else:
                yield FileType.FILE, f

        yield FileType.RET, os.path.dirname(fpath)

    def gen_header(self, what, fpath):
        if what == FileType.FILE:
            attr = c.IPMSG_FILE_REGULAR
            fname = os.path.basename(fpath)
            size = os.path.getsize(fpath)
        elif what == FileType.DIR:
            attr = c.IPMSG_FILE_DIR
            fname = os.path.basename(fpath)
            size = sum(os.path.getsize(os.path.join(fpath, f)) for f in os.listdir(fpath))
        elif what == FileType.RET:
            attr = c.IPMSG_FILE_RETPARENT
            fname = '.'
            size = 0
        size = long(size)
        header = ':%s:%s:%s:' % (fname, shex(size), shex(attr))
        hsize = shex((len(header) + 4))
        hsize = '0' * (4 - len(hsize)) + hsize
        header = hsize + header
        return header

    def send_file_data(self, path):
        sz = os.path.getsize(path)
        if sz > MIN_MMAP_SIZE:
            #self.flush()
            self.send_file_data_fast(path, sz + self._buffer.tell() < MIN_BUF_SIZE)
        else:
            self.send_file_data_slow(path)

    def send_file_data_slow(self, path):
        header = self.gen_header(FileType.FILE, path)
        f = open(path, 'rb')
        s = f.read()
        f.close()
        if self.what == FileType.DIR:
            self.buffer(header)
        self.buffer(s)

    def send_file_data_fast(self, path, to_buffer=False):
        header = self.gen_header(FileType.FILE, path)
        if self.what == FileType.DIR:
            if to_buffer:
                self.buffer(header)
            else:
                self.flush()
                self.request.send(header)
        with open(path, 'rb') as f:
            size = os.path.getsize(path)
            block_sz = MMAP_BLOCK_SIZE
            offset = 0
            while offset < size:
                sz = (offset + block_sz <= size) and block_sz or size - offset
                mp = mmap.mmap(f.fileno(), sz, flags=mmap.MAP_SHARED, prot=mmap.PROT_READ, offset=offset)
                if to_buffer:
                    self.buffer(mp[:])
                else:
                    self.flush()
                    self.request.sendall(mp)
                mp.close()
                offset += sz

    def get_file_info(self, raw):
        msgstr = ''
        ver, cntr, name, host, tag, msgstr = re.split(":", raw, 5)
        data = list(re.split('\0', msgstr))

        if int(tag) & 0xFF == c.IPMSG_GETFILEDATA:
            ref_cntr, fid, offset = re.split(':', data[0], 2)
            return FileType.FILE, (ref_cntr, fid, offset)
        elif int(tag) & 0xFF == c.IPMSG_GETDIRFILES:
            ref_cntr, fid, offset = re.split(':', data[0], 2)
            return FileType.DIR, (ref_cntr, fid)
        else:
            return FileType.UNKNOWN, None

class UploadStatus:
    STOP, START, FINISH, ERROR = range(4)

class ForkedTCPServer(SocketServer.TCPServer, SocketServer.ForkingMixIn):
    def __init__(self, addr, handler, share_list, upload_status):
        SocketServer.TCPServer.__init__(self, addr, handler)
        self.share_list = share_list
        self.upload_status = upload_status
        self.clients = {}

    def get_fileinfo(self, fid, (ip, port)):
        return filter((lambda (fileid, fpath, addr, sid) : fileid == fid and ip == addr[0]), self.share_list)

    def register(self, addr, fid):
        qid = time.time()
        self.clients[qid] = [addr, fid]
        self.upload_status[fid] = UploadStatus.START
        return qid

    def notify_error(self, qid):
        addr, fid = self.clients[qid]
        self.upload_status[fid] = UploadStatus.ERROR

    def notify_finish(self, qid):
        addr, fid = self.clients[qid]
        self.upload_status[fid] = UploadStatus.FINISH

