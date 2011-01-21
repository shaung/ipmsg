# -*- coding: utf-8 -*-

import socket, re, sys, os, os.path
import time, mmap, io, logging
import SocketServer, SimpleHTTPServer
from multiprocessing import Process, Queue

from ipmsg import consts as c
from ipmsg.config import settings
from ipmsg.message import engine
from ipmsg.util import *

logger = logging.getLogger('Download')

class DownloadError(Exception):
    pass

class Progress:
    (INIT, RECV, DONE, ERROR) = range(4)

    def __init__(self, **kws):
        self.start_time = time.time()
        self.prev_time = time.time()
        self.curr_time = time.time()
        self.curr_count = 0
        self.prev_size = 0
        self.curr_size = 0
        self.curr_speed = 0
        self.avg_speed = 0
        self.status = Progress.INIT

    def update(self, count=0, size=0):
        self.prev_time = self.curr_time
        self.curr_time   = time.time()
        self.curr_count += count
        self.prev_size  = self.curr_size
        self.curr_size  += size
        curr_speed = (self.curr_size - self.prev_size) / (self.curr_time - self.prev_time)
        if self.curr_speed == 0:
            self.curr_speed = curr_speed
        else:
            self.curr_speed   = (self.curr_speed + curr_speed ) / 2
        self.avg_speed   = (self.curr_size) / (self.curr_time - self.start_time)
        self.status      = Progress.RECV

    def finish(self):
        self.update()
        self.status = Progress.DONE

    def error(self):
        self.update()
        self.status = Progress.ERROR

    def is_error(self):
        return self.status == Progress.ERROR

    def is_done(self):
        return self.status == Progress.DONE

    def is_receiving(self):
        return self.status == Progress.RECV

    def __unicode__(self):
        return '%s%s' % (self.curr_time, self.curr_size)

    def __str__(self):
        return '%s%s' % (self.curr_time, self.curr_size)

    def __hash__(self):
        return str(self.curr_time) + str(self.curr_size)

class FileDownloader:
    def __init__(self, progress, addr):
        self.progress_entry = progress
        self.addr = addr
        self.total_size = 0
        self.sock = None

    def init_progress(self):
        self.pid = os.getpid()
        self.progress = Progress()
        self.progress_entry[self.pid] = self.progress

    def update_progress(self, *args):
        self.progress.update(*args)
        self.progress_entry[self.pid] = self.progress

    def finish_progress(self, *args):
        self.progress.finish(*args)
        self.progress_entry[self.pid] = self.progress

    def notify_error(self, *args):
        self.progress.error(*args)
        self.progress_entry[self.pid] = self.progress

    def download(self, atts, base_dir):
        self.init_progress()
        try:
            self.download_all(atts, base_dir)
        except DownloadError:
            self.notify_error()
        except:
            self.notify_error()
        finally:
            self.close_tcpsock()

    def download_all(self, atts, base_dir):
        start_time = time.time()
        for att in atts:
            msg = "%s:%s:" % (shex(long(att.cntr)), att.id)
            self.msg = msg
            attr = int(att.attr, 16)
            if attr == c.IPMSG_FILE_DIR:
                self.request_dir(msg)
                self._get_dir(att, base_dir)
            elif attr == c.IPMSG_FILE_REGULAR:
                self.request_file(msg)
                self._get_file_data(os.path.join(base_dir, att.name), int(att.size, 16), True)
            else:
                raise DownloadError, 'Unknown file attribute'

        self.finish_progress()
        finish_time = time.time()

    def _get_dir(self, att, base_dir):
        ip, port = self.addr

        fpath = base_dir
        depth = 0
        while depth >= 0:
            hdr_sz = self.sock.recv(4)
            file_info = self.sock.recv(int(hdr_sz, 16) - 4)
            fname, total_sz, attr, ext = re.split(':', file_info[1:], 3)
            if int(attr, 16) == c.IPMSG_FILE_REGULAR:
                self._get_file_data(os.path.join(fpath, fname), int(total_sz, 16))
            elif int(attr, 16) == c.IPMSG_FILE_DIR:
                fpath = os.path.join(fpath, fname)
                try:
                    os.mkdir(fpath)
                except:
                    raise DownloadError, 'Failed creating folder: %s' % fpath
                depth += 1
            elif int(attr, 16) == c.IPMSG_FILE_RETPARENT:
                fpath = os.path.dirname(fpath)
                depth -= 1
                if depth == 0: break
 
    def _get_file_data(self, fname, size, to_retry=False):
        logger.debug('size:%s' % size)
        self.update_progress(1, 0)
        self.total_size += size
        # FIXME: do not use mmap
        if True:
            self._get_file_data_slow(fname, size, to_retry)
        else:
            self._get_file_data_mmap(fname, size, to_retry)

    def _get_file_data_slow(self, fname, size, to_retry):
        f = open(fname, 'w+b')
        if size == 0:
            f.close()
            self.update_progress(0, 0)
            return

        block_sz = 0x4000000 # 40mb block
        sz = size # bytes remained
        buf = ''
        while sz > 0:
            try:
                s = self.sock.recv(min(block_sz, sz))
                self.update_progress(0, len(s))
                sz -= len(s)
                buf += s
                if(len(buf) >= block_sz):
                    f.write(buf)
                    f.flush()
                    buf = ''
            except socket.error as e:
                logger.debug('socket error, retrying')
                if to_retry:
                    to_retry = False
                    self.request_file(self.msg, size - sz)
                    sz = size
                    buf = ''
                else:
                    logger.debug('socket error, give up')
                    logger.debug('oops: %s' % str(e))
                    raise
            except Exception as e:
                logger.debug('oops: %s' % str(e))
                raise

        f.write(buf)
        f.close()
        self.update_progress(0, len(buf))

    # FIXME: mmap does not work for files larger than 2GB on 32bit systems,
    #        because the offset parameter must be signed integer.
    def _get_file_data_mmap(self, fname, size, to_retry = False):
        f = open(fname, 'w+b')

        if size == 0:
            f.flush()
            f.close()
            self.update_progress(0, 0)
            return
        else:
            f.seek(size-1)
            f.write('x')
            f.flush()

        block_sz = 0x4000000 # 40mb block
        max_map_sz = 0x40000000 # upto 1gb
        offset = 0
        recved = 0
        mp = mmap.mmap(f.fileno(), size <= max_map_sz and size or max_map_sz, flags=mmap.MAP_SHARED, prot=mmap.PROT_WRITE)

        while recved < size:
            try:
                s = self.sock.recv(min(size - recved, block_sz))
                if len(s) == 0:
                    raise DownloadError, 'nothing recieved'
                mp[recved - offset:recved - offset + len(s)] = s
                recved += len(s)
                self.update_progress(0, len(s))
                if recved - offset >= max_map_sz:
                    offset = recved
                    mp.flush()
                    mp.close()
                    logger.debug('map remap size(%s) offset(%s)' % (size, offset))
                    mp = mmap.mmap(f.fileno(), min(size - offset, max_map_sz), flags=mmap.MAP_SHARED, prot=mmap.PROT_WRITE, offset=offset)
            except socket.error:
                logger.debug('socket error, retrying')
                if to_retry:
                    to_retry = False
                    self.request_file(self.msg, recved)
                else:
                    logger.debug('socket error, give up')
                    raise
                    break
            except Exception as e:
                logger.debug('oops:%s' % str(e))
                raise
                break

        mp.flush()
        mp.close()
        f.close()

    def request_dir(self, msg):
        tag = c.IPMSG_GETDIRFILES
        self._request_file_data(tag, msg)

    def request_file(self, msg, offset = 0):
        tag = c.IPMSG_GETFILEDATA
        msg += shex(offset)
        self._request_file_data(tag, msg)

    def _request_file_data(self, tag, msg):
        self.reconnect_file_server()
        while True:
            try:
                raw = engine.make_raw(tag, msg)
                self.sock.send(raw)
            except:
                logger.debug('socket send error')
                self.reconnect_file_server()
            else:
                logger.debug('connected')
                return

    def get_tcpsock(self):
        self.close_tcpsock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 0))
        return self.sock

    def close_tcpsock(self):
        if not self.sock:
            return
        self.sock.close()
        self.sock = None

    def reconnect_file_server(self):
        self.get_tcpsock()
        logger.debug('connecting to...%s' % ':'.join([str(x) for x in self.addr]))
        self.sock.connect(self.addr)

