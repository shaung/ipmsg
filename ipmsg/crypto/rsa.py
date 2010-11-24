# -*- coding: utf-8 -*-

from M2Crypto import RSA

class RSAKey:
    def __init__(self, key = None, size = 1024, tuple = None):
        if key:
            self.key = key
        elif tuple:
            self.key = RSA.new_pub_key(tuple)
        else:
            self.key = RSA.gen_key(size, 65537)

    def encrypt(self, plain):
        rslt = self.key.public_encrypt(plain, RSA.pkcs1_padding)
        return rslt

    def decrypt(self, enc):
        rslt = self.key.private_decrypt(enc, RSA.pkcs1_padding)
        return rslt

    def export_key(self, path, cbfunc):
        self.key.save_key(path, callback = cbfunc)

    def get_pubkey_tuple(self):
        return self.key.pub()

    @classmethod
    def load_from_file(cls, fname, passphrase=''):
        k = RSA.load_key(fname, callback = lambda x : passphrase)
        return cls(key = k)

