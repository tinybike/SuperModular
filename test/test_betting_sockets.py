from flask import session, request, escape
from dyffy.utils import *
from dyffy import app, db, socketio
from decimal import *
import unittest
from socket_test import SocketTest

class TestBettingSockets(SocketTest):
    """
    Betting-related WebSocket tests
    TODO fix "bet on undefined could not be placed" @ 100 DYF full bet on +
    """
    def setUp(self):
        SocketTest.setUp(self)
        self.predict_market = 'Bitcoin'
        self.battle_coin = {
            'left': 'Dogecoin',
            'right': 'Bitcoin',
        }
        self.keys = ('price', 'price_change', 'price_ratio', 'last_update')
        self.tables = ('altcoin_bets', 'altcoin_bet_history',
                       'altcoin_vs_bets', 'altcoin_vs_bet_history')
        self.bet_amounts = (0.01, 0.1, 1, 10)
        # Quantize the bets for precision
        self.precision = '.00000001'
        self.bet_amounts = [Decimal(bet).quantize(Decimal(self.precision), \
            rounding=ROUND_HALF_EVEN) for bet in self.bet_amounts]
        self.denomination = 'DYF'
        self.number_of_bets = 3

    def test_get_current_prices_predict(self):
        """WebSocket: /socket.io/get-current-prices (predict)"""
        intake = {
            'emit-name': 'get-current-prices',
            'coin': self.predict_market,
        }
        signal, data = self.socket_emit_receive(intake)
        self.assertEqual(signal, 'current-prices')
        for key in self.keys:
            self.assertIn(key, data)
            self.assertIsNotNone(data[key])
        self.assertEqual(type(data['price_ratio']), float)
        self.assertTrue(0 <= data['price_ratio'] <= 1)
        self.assertEqual(type(data['last_update']), int)

    def test_get_current_prices_battle(self):
        """WebSocket: /socket.io/get-current-prices (battle)"""
        for side in ('left', 'right'):
            intake = {
                'emit-name': 'get-current-prices',
                'coin': self.battle_coin[side],
                'battle': side,
            }
            signal, data = self.socket_emit_receive(intake)
            self.assertEqual(signal, 'current-%s-prices' % side)
            for key in self.keys:
                self.assertIn(key, data)
                self.assertIsNotNone(data[key])
            self.assertEqual(type(data['price_ratio']), float)
            self.assertTrue(0 <= data['price_ratio'] <= 1)
            self.assertEqual(type(data['last_update']), int)

    def test_get_dyff_balance(self):
        """WebSocket: /socket.io/get-dyff-balance"""
        intake = {'emit-name': 'get-dyff-balance'}
        signal, data = self.socket_emit_receive(intake)
        self.assertEqual(signal, 'dyff-balance')
        self.assertEqual(data['balance'], 100)

    def test_get_time_remaining(self):
        """WebSocket: /socket.io/get-time-remaining"""
        intake = {'emit-name': 'get-time-remaining'}
        signal, data = self.socket_emit_receive(intake)
        self.assertEqual(signal, 'time-remaining')
        self.assertEqual(type(data['time_remaining']), str)
        minutes, seconds = map(int, data['time_remaining'].split(':'))
        self.assertTrue(0 <= minutes <= 60)
        self.assertTrue(0 <= seconds <= 60)

    def test_predict_bets(self):
        """WebSocket: /socket.io/predict-bets"""
        intake = {
            'emit-name': 'predict-bets',
            'coin': self.predict_market,
        }
        signal, data = self.socket_emit_receive(intake)
        self.assertEqual(signal, 'predict-data')
        self.assertIn('bets_down', data)
        self.assertIn('bets_up', data)
        self.assertIn('starting_price', data)
        self.assertIsNotNone(data['bets_down'])
        self.assertIsNotNone(data['bets_up'])
        self.assertIsNotNone(data['starting_price'])
        # data['bets_*'] should be a list-of-lists, where each row is:
        # [user name, amount of bet, denomination of bet, time of bet]
        for direction in ('bets_down', 'bets_up'):
            self.assertEqual(type(data[direction]), list)
            for bet in data[direction]:
                self.assertEqual(type(bet), list)
                self.assertEqual(type(bet[0]), str)
                self.assertIn(bet[0], self.all_users)
                self.assertEqual(type(bet[1]), float)
                self.assertGreater(bet[1], 0)
                self.assertEqual(type(bet[2]), str)
                self.assertEqual(type(bet[3]), str)
        self.assertEqual(type(data['starting_price']), dict)
        self.assertIn('price', data['starting_price'])
        self.assertEqual(type(data['starting_price']['price']), float)
        self.assertGreater(data['starting_price']['price'], 0)

    def test_battle_bets(self):
        """WebSocket: /socket.io/battle-bets"""
        intake = {
            'emit-name': 'battle-bets',
            'left': self.battle_coin['left'],
            'right': self.battle_coin['right'],
        }
        signal, data = self.socket_emit_receive(intake)
        self.assertEqual(signal, 'battle-data')
        self.assertIn('bets_left', data)
        self.assertIn('bets_right', data)
        self.assertIn('current_price', data)
        self.assertIsNotNone(data['bets_left'])
        self.assertIsNotNone(data['bets_right'])
        self.assertIsNotNone(data['current_price'])
        # data['bets_*'] should be a list-of-lists, where each row is:
        # [user name, amount of bet, denomination of bet, time of bet]
        for direction in ('bets_left', 'bets_right'):
            self.assertEqual(type(data[direction]), list)
            for bet in data[direction]:
                self.assertEqual(type(bet), list)
                self.assertEqual(type(bet[0]), str)
                self.assertIn(bet[0], self.all_users)
                self.assertEqual(type(bet[1]), float)
                self.assertGreater(bet[1], 0)
                self.assertEqual(type(bet[2]), str)
                self.assertEqual(type(bet[3]), str)
        self.assertEqual(type(data['current_price']), dict)
        for target in ('left', 'right'):
            self.assertIn(target, data['current_price'])
            self.assertEqual(type(data['current_price'][target]), float)
            self.assertGreater(data['current_price'][target], 0)

    def test_predict_bet_minus(self):
        """WebSocket: /socket.io/predict-bet (-)"""
        self.predict_bet('-')

    def test_predict_bet_plus(self):
        """WebSocket: /socket.io/predict-bet (+)"""
        self.predict_bet('+')

    def predict_bet(self, direction):
        total_amount = 0
        for j, amount in enumerate(self.bet_amounts):
            # Test first bet (insert) and follow-up bets (update)
            for i in xrange(1, self.number_of_bets+1):
                print "#", i, "betting", amount, "on", direction
                total_amount += amount
                print "(total bet so far: " + str(total_amount) + ")"
                intake = {
                    'emit-name': 'predict-bet',
                    'amount': amount,
                    'denomination': self.denomination,
                    'market': self.predict_market,
                    'direction': direction,
                }
                signal, data = self.socket_emit_receive(intake)
                self.assertEqual(signal, 'predict-bet-response')
                self.assertTrue(data['success'])
                self.assertIsNotNone(data['time_of_bet'])
                self.assertEqual(type(data['time_of_bet']), str)
                self.assertEqual(data['coin'], self.predict_market)
                self.assertEqual(data['denomination'],
                                self.denomination)
                self.assertEqual(data['bet_direction'], direction)
                query = (
                    "SELECT better, amount, denomination, bet_direction "
                    "FROM %s WHERE better = %%s"
                )
                for table in ('altcoin_bets', 'altcoin_bet_history'):
                    stored_bet = None
                    with db.cursor_context(True) as cur:
                        cur.execute(query % table, (self.username,))
                        if table == 'altcoin_bets':
                            self.assertEqual(cur.rowcount, 1)
                            stored_bet = cur.fetchone()
                        else:
                            self.assertEqual(cur.rowcount,
                                             i + j*self.number_of_bets)
                            stored_bet = cur.fetchall()[-1]
                        print "stored bet:", stored_bet
                    self.assertIsNotNone(stored_bet)
                    self.assertEqual(stored_bet['better'], self.username)
                    if table == 'altcoin_bets':
                        self.assertEqual(stored_bet['amount'], total_amount)
                    else:
                        self.assertEqual(stored_bet['amount'], amount)
                    self.assertEqual(stored_bet['denomination'],
                                     self.denomination)
                    self.assertEqual(stored_bet['bet_direction'],
                                     direction)

    def test_battle_bet_right(self):
        """WebSocket: /socket.io/battle-bet (right)"""
        self.battle_bet('right')

    def test_battle_bet_left(self):
        """WebSocket: /socket.io/battle-bet (left)"""
        self.battle_bet('left')

    def battle_bet(self, target):
        total_amount = 0
        for j, amount in enumerate(self.bet_amounts):
            # Test first bet (insert) and follow-up bets (update)
            for i in xrange(1, self.number_of_bets+1):
                print "#", i, "betting", amount, "on", target
                total_amount += amount
                intake = {
                    'emit-name': 'battle-bet',
                    'amount': amount,
                    'denomination': self.denomination,
                    'left': self.battle_coin['left'],
                    'right': self.battle_coin['right'],
                    'target': self.battle_coin[target],
                }
                signal, data = self.socket_emit_receive(intake)
                self.assertEqual(signal, 'battle-bet-response')
                self.assertTrue(data['success'])
                self.assertIsNotNone(data['time_of_bet'])
                self.assertEqual(type(data['time_of_bet']), str)
                self.assertEqual(data['left_coin'],
                                 self.battle_coin['left'])
                self.assertEqual(data['right_coin'],
                                 self.battle_coin['right'])
                self.assertEqual(data['denomination'],
                                 self.denomination)
                self.assertEqual(data['bet_target'],
                                 currency_codes(self.battle_coin[target],
                                                convert_from="name",
                                                convert_to="symbol"))
                query = (
                    "SELECT better, amount, denomination, bet_target "
                    "FROM %s WHERE better = %%s"
                )
                for table in ('altcoin_vs_bets', 'altcoin_vs_bet_history'):
                    stored_bet = None
                    with db.cursor_context(True) as cur:
                        cur.execute(query % table, (self.username,))
                        if table == 'altcoin_vs_bets':
                            self.assertEqual(cur.rowcount, 1)
                            stored_bet = cur.fetchone()
                        else:
                            self.assertEqual(cur.rowcount,
                                             i + j*self.number_of_bets)
                            stored_bet = cur.fetchall()[-1]
                        print "stored bet:", stored_bet
                    self.assertIsNotNone(stored_bet)
                    self.assertEqual(stored_bet['better'], self.username)
                    if table == 'altcoin_vs_bets':
                        self.assertEqual(stored_bet['amount'], total_amount)
                    else:
                        self.assertEqual(stored_bet['amount'], amount)
                    self.assertEqual(stored_bet['denomination'],
                                     self.denomination)
                    self.assertEqual(stored_bet['bet_target'],
                                     currency_codes(self.battle_coin[target],
                                                convert_from="name",
                                                convert_to="symbol"))

    def tearDown(self):
        delete_query = "DELETE FROM %s WHERE better = %%s"
        reset_dyffs_query = (
            "UPDATE dyffs SET balance = 100 WHERE username = %s"
        )
        select_dyffs_query = "SELECT balance FROM dyffs WHERE username = %s"
        with db.cursor_context() as cur:
            for table in self.tables:
                cur.execute(delete_query % table, (self.username,))
            cur.execute(reset_dyffs_query, (self.username,))
            cur.execute(select_dyffs_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 100)

if __name__ == '__main__':
    unittest.main()
