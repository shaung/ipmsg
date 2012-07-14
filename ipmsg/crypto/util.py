# -*- coding: utf-8 -*-

from rsa.randnum import read_random_bits

def rand_bytes(nbytes):
    return read_random_bits(nbytes * 8)
