from __future__ import division
import os, sys, json
from decimal import *

from flask import session, escape, request
import werkzeug

from dyffy.models import User
from dyffy.utils import *
from dyffy import app, db, routes, sockets

import unittest

class TestCharts(unittest.TestCase):

    def setUp(self):
        self.username = u'testify'
        self.password = u'testifier'

    def test_socket(self):
        """WebSocket: /socket.io/charts"""
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
            self.assertIn('user', session)
            self.assertEquals(session['user'], self.username)
            intake = {}

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()