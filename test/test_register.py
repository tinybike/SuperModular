from __future__ import division
import os, sys, random, string
import bcrypt, hashlib
from decimal import *
from Crypto.Cipher import AES

from flask import session, escape, request
import werkzeug

from dyffy.models import User
from dyffy.guard import Guard
from dyffy.utils import *
from dyffy import app, db, routes

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup
import unittest

app.testing = True
app.config['WTF_CSRF_ENABLED'] = False

ENVIRON_BASE = {'HTTP_USER_AGENT': 'Chrome', 'REMOTE_ADDR': '127.0.0.1'}
guard = Guard()

class TestRegister(unittest.TestCase):
    """
    Unit tests for the /register route, using randomly generated usernames,
    passwords, account numbers, and secret keys.
    """
    def setUp(self):
        self.account = 'r' + guard.id_generator(33)
        self.secret = 's' + guard.id_generator(28)
        self.password = guard.id_generator(random.randint(0, 250))
        self.username = guard.id_generator(random.randint(0, 20))
        self.email = guard.id_generator(random.randint(0, 10)) + '@' + \
            guard.id_generator(random.randint(0, 10)) + '.com'

    def test_route_register_get(self):
        """Route: HTTP GET /register"""
        with app.test_client() as client:
            get_response = client.get('/register')
            self.assertEquals(get_response.status_code, 200)
            title = BeautifulSoup(get_response.data)('title')[0]
            self.assertEqual(title.contents[0], u'crypto.cab')

    def test_check_username_taken(self):
        '''Route: HTTP POST /register (verify that usernames are unique)'''
        # Randomly generated username should not be taken
        self.assertFalse(routes.check_username_taken(self.username))
        # Username 'Jack' should be taken
        self.assertTrue(routes.check_username_taken('Jack'))

    def test_insert_user(self):
        '''Route: HTTP POST /register (insert new user into database)'''
        insert_result, encrypted_secret, iv = routes.insert_user(
            self.username,
            self.password,
            self.email,
            self.account,
            self.secret
        )
        # Make sure the database insert returned something (the user id);
        # if the insert failed, insert_result is None.
        self.assertIsNotNone(insert_result)
        # If the insert succeeded, insert_result is the user id, which is
        # a long integer (i.e., bigserial postgres data type).
        self.assertEqual(type(insert_result), long)
        # Make sure the AES ciphertext and initialization vector are the
        # correct lengths (32 and 16 bytes, respectively).
        self.assertEqual(len(encrypted_secret), 32)
        self.assertEqual(len(iv), 16)
        # Encrypt the input secret using the AES cipher to make sure the
        # ciphertext and initialization vectors exactly match the app's.
        encryptor = AES.new(hashlib.sha256(self.password).digest(),
                            AES.MODE_CBC, IV=iv)
        verify_secret = encryptor.encrypt(self.secret + 'XXX')
        self.assertEqual(len(verify_secret), 32)
        self.assertEqual(encrypted_secret, verify_secret)
        # Make sure grant_dyffs procedure was triggered for the new user
        # and their balance has been set correctly (to 100 dyffs).
        select_dyffs_query = "SELECT balance FROM dyffs WHERE username = %s"
        balance = None
        with db.cursor_context() as cur:
            cur.execute(select_dyffs_query, (self.username,))
            if cur.rowcount:
                balance = cur.fetchone()[0]
        self.assertIsNotNone(balance)
        self.assertEqual(type(balance), Decimal)
        self.assertEqual(balance, Decimal(100))
        
    def test_create_session(self):
        '''Route: HTTP POST /register (session creation and login)'''
        user_id, encrypted_secret, iv = routes.insert_user(
            self.username,
            self.password,
            self.email,
            self.account,
            self.secret
        )
        with app.test_client() as client:
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            post_response = client.post('/login',
                data=login_data,
                follow_redirects=True
            )
            self.assertEquals(post_response.status_code, 200)
            self.assertIsNotNone(session)
            self.assertEquals(session['user'], self.username)
            self.assertFalse(session['admin'])
            self.assertEqual(type(session), werkzeug.local.LocalProxy)
            self.assertTrue('user' in session)
            self.assertTrue('admin' in session)
            self.assertTrue('secret' in session)
            self.assertTrue('address' in session)
            self.assertTrue('_id' in session)
            self.assertTrue('_fresh' in session)
            self.assertTrue(session['_fresh'])
            self.assertFalse(session['admin'])
            user = User(user_id, self.username, self.email,
                        self.account, self.secret, iv)
            routes.login_user(user)
            self.assertIsNotNone(user)
            self.assertEqual(self.username, escape(user.username))
            self.assertEqual(self.username, session['user'])
            self.assertEqual(escape(user.username), session['user'])

    def tearDown(self):
        delete_user_query = "DELETE FROM users WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(delete_user_query, (self.username,))
        select_user_query = "SELECT count(*) FROM users WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(select_user_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()