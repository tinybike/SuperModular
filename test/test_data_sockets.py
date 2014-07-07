from flask import session, request, escape
from dyffy.utils import *
from dyffy import app, db, socketio
from decimal import *
import unittest
from socket_test import SocketTest

class TestDataSockets(SocketTest):

    def setUp(self):
        SocketTest.setUp(self)
        self.frequency = '8H'
        self.currency1 = {
            'symbol': 'BTC',
            'name': currency_codes('BTC'),
        }
        self.currency2 = {
            'symbol': 'USD',
            'name': currency_codes('USD'),
        }

    def test_charts(self):
        """WebSocket: /socket.io/request-chart-data"""
        signal, data = self.socket_emit_receive({
            'emit-name': 'request-chart-data',
            'freq': self.frequency,
            'currency1': self.currency1['symbol'],
            'currency2': self.currency2['symbol'],
        })
        self.assertEqual(signal, 'chart-data')
        self.assertIn('data', data)
        self.assertIn('name', data)
        self.assertEqual(data['name'], self.currency1['name'])
        signal, data = self.socket_emit_receive({
            'emit-name': 'request-chart-data',
            'freq': self.frequency,
            'currency1': self.currency2['symbol'],
            'currency2': self.currency1['symbol'],
        })
        self.assertEqual(signal, 'chart-data')
        self.assertIn('data', data)
        self.assertIn('name', data)
        self.assertEqual(data['name'], self.currency1['name'])

    def tearDown(self):
        reset_dyffs_query = (
            "UPDATE dyffs SET balance = 100 WHERE username = %s"
        )
        select_dyffs_query = "SELECT balance FROM dyffs WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(reset_dyffs_query, (self.username,))
            cur.execute(select_dyffs_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 100)

if __name__ == '__main__':
    unittest.main()
