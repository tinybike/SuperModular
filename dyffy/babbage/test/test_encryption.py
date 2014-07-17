from __future__ import division
import os, sys, random, base64
import bcrypt, hashlib
import base64
from decimal import *
from bunch import Bunch
from Crypto.Cipher import AES
import unittest

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))

from guard import Guard
from utils import *

guard = Guard()

class TestEncryption(unittest.TestCase):
    """
    Tests for our cryptography algorithms.
    - User passwords are salted then stored as a bcrypt hash.
    - Ripple wallet secret keys are encrypted using AES.  The AES key is the
      SHA-256 digest of the user's password (32 bytes), and the 16 byte
      initialization vector is randomly generated.
    - Our implementation of AES/bcrypt methods uses the pycrypto
      (Crypto.Cipher), bcrypt, and hashlib (for SHA-256) modules.
    """
    def setUp(self):
        self.stored = Bunch()
        self.user_id = 0
        self.encryption_test_repeats = 100

    def encrypt_insert_select_decrypt(self):
        self.cipher_secret, self.iv = guard.AES_cipher(self.secret, self.password)
        self.assertEqual(len(self.iv), 16)
        self.assertEqual(len(self.cipher_secret), 32)
        parameters = {
            'username': self.username,
            'password': self.digest_password,
            'walletaddress': self.account,
            'walletsecret': base64.b64encode(self.cipher_secret),
            'iv': base64.b64encode(self.iv),
        }
        query = (
            "INSERT INTO users "
            "(username, password, joined, walletaddress, "
            "walletsecret, iv) "
            "VALUES "
            "(%(username)s, %(password)s, now(), %(walletaddress)s, "
            "%(walletsecret)s, %(iv)s) "
            "RETURNING user_id"
        )
        with cursor_context() as cur:
            cur.execute(query, parameters)
            res = cur.fetchone()
        self.assertIsNotNone(res)
        self.assertIsNotNone(res[0])
        self.user_id = res[0]
        query = (
            "SELECT user_id, password, email, walletaddress, walletsecret, iv, username "
            "FROM users WHERE user_id = %s"
        )
        with cursor_context(True) as cur:
            cur.execute(query, (self.user_id,))
            self.assertEqual(cur.rowcount, 1)
            for row in cur:
                self.stored.digest_password = row['password']
                self.stored.cipher_secret = base64.b64decode(row['walletsecret'])
                self.stored.iv = base64.b64decode(row['iv'])
        self.assertEqual(len(self.stored.cipher_secret), 32)
        self.assertEqual(len(self.stored.iv), 16)
        self.assertEqual(self.stored.cipher_secret, self.cipher_secret)
        self.assertEqual(self.stored.iv, self.iv)
        self.assertEqual(self.stored.digest_password, self.digest_password)
        self.stored.secret = guard.AES_clear(self.stored.cipher_secret, self.password, self.stored.iv)
        self.assertEqual(self.secret, self.stored.secret)
        self.assertEqual(self.secret, guard.AES_clear(self.cipher_secret, self.password, self.iv))

    def test_encryption(self):
        """Crypto randomization tests (AES key cipher, bcrypt password hash)"""
        for i in xrange(self.encryption_test_repeats):
            self.account = 'r' + guard.id_generator(33)  # ra6dtkHEhgaBCPE9XFMBDK6DyPNWCMkjbU
            self.secret = 's' + guard.id_generator(28)  # shaQZThtDVpcgvvqv5YcMCsu99JWq
            self.password = guard.id_generator(random.randint(0, 250))
            self.digest_password = guard.bcrypt_digest(self.password.encode('utf-8'))
            self.username = guard.id_generator(random.randint(0, 20))
            self.stored = Bunch()
            self.user_id = 0
            self.encrypt_insert_select_decrypt()
            with cursor_context() as cur:
                query = "DELETE FROM users WHERE username = %s"
                cur.execute(query, (self.username,))

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
