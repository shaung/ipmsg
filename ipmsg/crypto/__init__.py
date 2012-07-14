# -*- coding: utf-8 -*-

import logging, traceback

import re, binascii, os.path
from _rsa import RSAKey
from cipher import Cipher
from ipmsg import consts as c
from ipmsg.util import shex

logger = logging.getLogger(__file__)

class CryptoError(Exception):
    pass

class EncryptionError(CryptoError):
    pass

class DecryptionError(CryptoError):
    pass


CIPHERS = { \
    c.IPMSG_BLOWFISH_128 : ('Blowfish', 128),  \
    c.IPMSG_BLOWFISH_256 : ('Blowfish', 256),  \
    c.IPMSG_RC2_40       : ('RC2', 40),  \
    c.IPMSG_RC2_128      : ('RC2', 128),  \
    c.IPMSG_RC2_256      : ('RC2', 256),  \
    c.IPMSG_AES_128      : ('AES', 128),  \
}

RSALEN = { \
    c.IPMSG_RSA_1024 : 1024, \
    c.IPMSG_RSA_2048 : 2048, \
    c.IPMSG_RSA_512  : 512, \
}

class Crypto:
    def __init__(self):
        self.contact_keys = {}
        self.contact_capa = {}
        self.passphrase = 'silentdays'
        self._init_rsa_key()

    def knows(self, addr):
        return addr in self.contact_capa and addr in self.contact_keys

    def understands(self, addr):
        if not self.knows(addr):
            return False

        capa = self.contact_capa[addr] & self.encrypt_capa
        methods = self.get_methods(shex(capa))
        if None in methods:
            return False

        return True

    def get_pubkey_raw(self, addr):
        capa = self.contact_capa[addr] & self.encrypt_capa
        logger.debug('try get_pubkey_raw: capa=%s' % (capa))
        rsa_tag, cipher_tag = self.get_methods(shex(capa))
        logger.debug('try get_pubkey_raw: rsa_tag=%s' % (rsa_tag))
        if not rsa_tag:
            capa = self.encrypt_capa
            rsa_tag = c.IPMSG_RSA_1024
        logger.debug('try get_pubkey_raw: %s' % (repr(addr)))
        raw = shex(capa) + ':' + self.get_pubkey_hex(rsa_tag)
        logger.debug('get_pubkey_raw: %s' % raw)
        return raw

    def get_pubkey_hex(self, rsa_tag):
        logger.debug('try get_pubkey_hex: %s' % rsa_tag)
        key = self.key[RSALEN[rsa_tag]]
        logger.debug('key: %s' % key)
        logger.debug('get pubkey tuple')
        e, n = key.get_pubkey_tuple()
        logger.debug('key: e=%s, n=%s' % (e, n))
        e = shex(e)
        n = shex(n)
        e = binascii.a2b_hex('0'*(len(e)%2) + e)
        n = binascii.a2b_hex('0'*(len(n)%2) + n)
        logger.debug('key: e=%s, n=%s' % (e, n))
        key_hex = binascii.b2a_hex(e)[1:] + '-' + binascii.b2a_hex(n)
        logger.debug('got key_hex: %s' % (key_hex))
        return key_hex

    def memo(self, addr, capa, key=None):
        self.contact_capa[addr] = int(capa, 16)
        logger.debug('contact %s: capa=%s, key=%s' % (repr(addr), capa, key))
        if key:
            # key = EE-NNNN....
            e, n = re.split('-', key, 1)
            if len(e) % 2 != 0: e = '0' + e
            l = len(n) * 4
            if l not in RSALEN.values():
                return
            e = int(e, 16)
            n = int(n, 16)
            logger.debug('contact %s: e=%s, n=%s' % (repr(addr), e, n))
            k = RSAKey(size=l, tuple=(e, n))
            if addr not in self.contact_keys:
                self.contact_keys[addr] = {}
            logger.debug('memorized %s: l=%s' % (repr(addr), l))
            self.contact_keys[addr][l] = k
            logger.debug('memorized %s: k=%s' % (repr(addr), self.contact_keys[addr][l]))

    def encrypt(self, msg, addr):
        logger.debug('before encryption')
        if not self.knows(addr):
            logger.debug('dont know who')
            return False, None

        logger.debug('checking methods')
        methods = self.get_methods(shex(self.contact_capa[addr]))
        if None in methods:
            logger.debug('dont have methods')
            return False, None

        rsa_tag, cipher_tag = methods
        logger.debug('methods checked: rsa_tag=%s, cipher_tag=%s' % (rsa_tag, cipher_tag))

        try:
            rsa_key = self.contact_keys[addr][RSALEN[rsa_tag]]
        except KeyError:
            logger.debug('does not have public key for %s, %s' % (repr(addr), RSALEN[rsa_tag]))
            return False, None

        logger.debug('got rsa key %s' % (RSALEN[rsa_tag]))
        cipher = Cipher(*CIPHERS[cipher_tag])
        logger.debug('ready to encypt cipher')
        enc_msg = cipher.encrypt(msg)
        enc_ses_key = rsa_key.encrypt(cipher.session_key)

        capa = shex(rsa_tag | cipher_tag)
        enc_raw = capa + ':' + binascii.b2a_hex(enc_ses_key) + ':' + binascii.b2a_hex(enc_msg)

        logger.debug('encryption ok')
        return True, enc_raw

    def get_methods(self, hex_capa):
        logger.debug('get encryption methods: capa=%s' % hex_capa)
        enc_capa = int(hex_capa, 16)

        rsa_tag = None
        for k in (c.IPMSG_RSA_1024, c.IPMSG_RSA_2048, c.IPMSG_RSA_512):
            if enc_capa & k == k:
                rsa_tag = k
                break

        if rsa_tag == c.IPMSG_RSA_512:
            cipher_list = [c.IPMSG_RC2_40, c.IPMSG_RC2_128, c.IPMSG_RC2_256]
        else:
            cipher_list = [c.IPMSG_BLOWFISH_128, c.IPMSG_BLOWFISH_256, c.IPMSG_AES_128]

        cipher_tag = None
        for x in cipher_list:
            if enc_capa & x == x:
                cipher_tag = x
                break

        return rsa_tag, cipher_tag

    def decrypt(self, raw):
        enc_capa, enc_session_key, enc_msg = re.split(':', raw, 2)

        rsa_tag, cipher_tag = self.get_methods(enc_capa)
        if not rsa_tag or not cipher_tag:
            logger.debug('no method specified: %s, %s' % (rsa_tag, cipher_tag))
            return False, None

        try:
            key = self.key[RSALEN[rsa_tag]]
            enc_session_key = binascii.a2b_hex(enc_session_key)
            session_key = key.decrypt(enc_session_key)
        except:
            logger.debug(traceback.format_exc())
            return False, None

        cipher = Cipher(*CIPHERS[cipher_tag], session_key=session_key)
        enc_msg = binascii.a2b_hex(enc_msg)
        dec_msg = cipher.decrypt(enc_msg)

        return True, dec_msg

    def _init_rsa_key(self):
        self.encrypt_capa = c.IPMSG_RSA_512 | c.IPMSG_RSA_1024 | c.IPMSG_BLOWFISH_128
        # FIXME: hard-coding path
        self.key_file = lambda x : os.path.expanduser('~/.ipmsg/rsa/rsa.%s.pem' % str(x))
        self._load_key()

    def _load_key(self):
        self.key = {}
        for i in RSALEN.values():
            try:
                self.key[i] = RSAKey.load_from_file(self.key_file(i), self.passphrase)
            except:
                self.key[i] = RSAKey(size = i)
                self.key[i].export_key(self.key_file(i), cbfunc = lambda x : self.passphrase)

    def _save_key(self):
        for i in RSALEN.values():
            self.key[i].export_key(self.key_file(i), cbfunc = lambda x : self.passphrase)

cry = Crypto()
