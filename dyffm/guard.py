#!/usr/bin/env python
"""
Security/cryptography methods for Dyffy.
"""
import sys, random, base64, string
import hashlib
from Crypto.Cipher import AES
from decimal import *
import bcrypt

class Guard(object):

    MISMATCH_ERROR = TypeError("inputs must be both unicode or both bytes")

    def AES_cipher(self, cleartext, password):
        key = hashlib.sha256(password).digest()
        iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
        encryptor = AES.new(key, AES.MODE_CBC, IV=iv)
        ciphertext = encryptor.encrypt(cleartext + 'XXX')
        return ciphertext, iv

    def AES_clear(self, ciphertext, password, iv):
        key = hashlib.sha256(password).digest()
        decryptor = AES.new(key, AES.MODE_CBC, IV=iv)
        return decryptor.decrypt(ciphertext)[:-3]

    def bcrypt_digest(self, password):
        return bcrypt.hashpw(password, bcrypt.gensalt())

    def check_password(self, password, digest):
        return self.const_time_compare(bcrypt.hashpw(password, digest), digest)

    def const_time_compare(self, a, b):
        result = False
        if isinstance(a, unicode):
            if not isinstance(b, unicode):
                raise MISMATCH_ERROR
        elif isinstance(a, bytes):
            if not isinstance(b, bytes):
                raise MISMATCH_ERROR
        else:
            raise MISMATCH_ERROR
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0

    def id_generator(self, size=6, chars=string.ascii_uppercase+string.ascii_lowercase+string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1] in config.ALLOWED_EXTENSIONS


if __name__ == '__main__':
    guard = Guard()
    print guard.id_generator(24)
    sys.exit()
