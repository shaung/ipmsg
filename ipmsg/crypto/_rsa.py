# -*- coding: utf-8 -*-

import rsa
import logging
logger = logging.getLogger(__file__)

class RSAKey:
    def __init__(self, key = None, size = 1024, tuple = None):
        if key:
            self.key = key
        elif tuple:
            e, n = tuple
            self.key = rsa.PublicKey(n, e)
        else:
            _, self.key = rsa.newkeys(size)

    def encrypt(self, plain):
        rslt = rsa.encrypt(plain, self.key)
        return rslt

    def decrypt(self, enc):
        logger.debug('try decrypt: %s' % (enc))
        rslt = rsa.decrypt(enc, self.key)
        logger.debug('decrypted: %s' % (rslt))
        return rslt

    def export_key(self, path, cbfunc):
        with open(path, 'wb') as f:
            content = self.key.save_pkcs1(format='PEM')
            f.write(content)

    def get_pubkey_tuple(self):
        pub_key = rsa.PublicKey(self.key.n, self.key.e)
        logger.debug('pub key: %s' % (pub_key))
        logger.debug('pub key: e=%s, n=%s' % (pub_key.e, pub_key.n))
        return pub_key.e, pub_key.n

    @classmethod
    def load_from_file(cls, fname, passphrase=''):
        content = open(fname, 'rb').read()
        k = rsa.PrivateKey.load_pkcs1(content, format='PEM')
        return cls(key = k)

