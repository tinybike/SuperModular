from flask import session
from dyffy import app, db, socketio
from contextlib import contextmanager
from decimal import *
import unittest

class SocketTest(unittest.TestCase):

    def setUp(self):
        getcontext().prec = 28
        self.username = u'testify'
        self.password = u'testifier'
        app.config['TESTING'] = True
        app.config['TESTUSER'] = self.username
        app.config['TESTPASS'] = self.password
        self.ns = '/socket.io/'
        self.client = socketio.test_client(app, namespace=self.ns)
        self.client.get_received(self.ns)
        select_user_id_query = "SELECT user_id FROM users WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute("SELECT username FROM users")
            self.assertGreater(cur.rowcount, 0)
            self.all_users = [row[0] for row in cur.fetchall()]
            cur.execute(select_user_id_query, (self.username,))
            self.assertEqual(cur.rowcount, 1)
            self.user_id = cur.fetchone()[0]
        for user in self.all_users:
            self.assertEqual(type(user), str)
        self.dyffs_default_balance = Decimal(100)

    def tearDown(self):
        pass

    def socket_emit_receive(self, intake):
        signal = None
        data = None
        emit_name = intake.pop('emit-name', None)
        if intake:
            self.client.emit(emit_name, intake, namespace=self.ns)
        else:
            self.client.emit(emit_name, namespace=self.ns)
        received = self.client.get_received(self.ns)
        if received:
            signal = received[0]['name']
            data = received[0]['args'][0]
            self.assertEqual(type(signal), str)
            self.assertEqual(type(data), dict)
        return signal, data

    @contextmanager
    def login(self):
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
            self.assertEqual(session['user'], self.username)
            yield client
