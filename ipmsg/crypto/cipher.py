# -*- coding: utf-8 -*-

import re
from Crypto.Cipher import Blowfish, ARC2
import util

import logging
logger = logging.getLogger(__file__)

class Cipher:
    algos = {'Blowfish': Blowfish , 'RC2' : ARC2}

    def __init__(self, name = 'Blowfish', size = 128, session_key = None, mode = None):
        logger.debug('Making cipher: name=%s, size=%s, session_key=%s, mode=%s' % (name, size, session_key, mode))
        assert(name in Cipher.algos.keys())
        assert(size in (128, 256))
        self.algo = Cipher.algos[name]
        self.size = size
        self.session_key = session_key or util.rand_bytes(self.size/8)
        logger.debug('making key with session-key=%s' % self.session_key)
        iv = '\0' * 8
        self.key = self.algo.new(key=self.session_key, mode=self.algo.MODE_CBC, IV=iv)
        logger.debug('key made')

    def encrypt(self, plain):
        logger.debug('cipher encrypt: %s' % plain)
        msg = plain
        msg += '\x00' * (8 - len(msg) % 8)
        enc_msg = self.key.encrypt(msg)
        logger.debug('cipher encrypted: %s' % enc_msg)
        return enc_msg

    def decrypt(self, enc_msg):
        logger.debug('cipher decrypt: %s' % enc_msg)
        dec_msg = self.key.decrypt(enc_msg)
        msg, _ = re.split('\0', dec_msg, 1)
        logger.debug('cipher decrypted: %s' % msg)
        return msg


