from __future__ import division
import os, sys

from flask import session, escape, request
from werkzeug.local import LocalProxy

from dyffy.models import User
from dyffy.utils import *
from dyffy import app, db, routes

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup
import unittest

app.testing = True
app.config['WTF_CSRF_ENABLED'] = False

class TestLogin(unittest.TestCase):
    """
    Tests for the /login route.
    """
    def setUp(self):
        self.username = u'testify'
        self.password = u'testifier'
        self.bad_username = u'not_a_real_user'
        self.bad_password = u'not_a_real_password'

    def test_route_login_get(self):
        """Route: HTTP GET /login"""
        with app.test_client() as client:
            get_response = client.get('/login')
            self.assertEqual(get_response.status_code, 200)
            title = BeautifulSoup(get_response.data)('title')[0]
            self.assertEqual(title.contents[0], u'crypto.cab')

    def test_route_login_valid(self):
        """Route: HTTP POST /login (valid credentials)"""
        user_id = self.get_stored_user_id()
        with app.test_client() as client:
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            post_response = client.post('/login',
                data=login_data,
                follow_redirects=True
            )
            self.assertEqual(post_response.status_code, 200)
            self.assertIn('user', session)
            # Make sure the session has data which match
            # the user's inputs, and has the correct fields
            self.assertEqual(session['user'], self.username)
            self.assertFalse(session['admin'])
            self.assertEqual(type(session), LocalProxy)
            self.assertTrue('user_id' in session)
            self.assertTrue('user' in session)
            self.assertTrue('admin' in session)
            self.assertTrue('secret' in session)
            self.assertTrue('address' in session)
            self.assertTrue('_id' in session)
            self.assertTrue('_fresh' in session)
            self.assertTrue(session['_fresh'])
            self.assertFalse(session['admin'])
            self.assertEqual(type(session['user_id']), unicode)
            self.assertEqual(session['user_id'], unicode(user_id))

    def test_route_login_invalid(self):
        """Route: HTTP POST /login (invalid credentials)"""
        user_id = self.get_stored_user_id()
        with app.test_client() as client:
            login_data = {
                'username': self.bad_username,
                'password': self.bad_password,
            }
            post_response = client.post('/login',
                data=login_data,
                follow_redirects=True
            )
            self.assertEquals(post_response.status_code, 200)
            self.assertNotIn('user', session)
            self.assertTrue('_flashes' in session)
            self.assertEqual(
                session['_flashes'][0],
                ('error', 'Username or password is invalid')
            )

    def get_stored_user_id(self):
        """Get stored user_id from database for comparison"""
        select_userid_query = "SELECT user_id FROM users WHERE username = %s"
        user_id = None
        with db.cursor_context() as cur:
            cur.execute(select_userid_query, (self.username,))
            if cur.rowcount:
                user_id = cur.fetchone()[0]
        self.assertIsNotNone(user_id)
        self.assertEquals(type(user_id), long)
        return user_id

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()