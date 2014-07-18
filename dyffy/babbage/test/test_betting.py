from decimal import *
import unittest
from base_test import BaseTest
import config

class TestBetting(BaseTest):

    def setUp(self):
        BaseTest.setUp(self)
        self.battle = {
            "red": {
                "artist": "darkmatter",
                "song": "1-1arr3"
            },
            "blue": {
                "artist": "eatdatcake",
                "song": "zigga-zig-caked-up-feat-the-spice-girls-free-download"
            }
        }
        self.keys = ('price', 'price_change', 'price_ratio', 'last_update')
        self.tables = config.BET_TABLES + config.BET_HISTORY_TABLES
        self.bet_amounts = (0.01, 0.1, 1, 10)
        self.precision = '.00000001'
        self.bet_amounts = [Decimal(bet).quantize(Decimal(self.precision), \
            rounding=ROUND_HALF_EVEN) for bet in self.bet_amounts]
        self.denomination = 'DYF'
        self.number_of_bets = 3
        self.currencies = {}
        self.battle_symbol = {
            'left': currency_codes(self.battle['left'],
                                   convert_from="name",
                                   convert_to="symbol"),
            'right': currency_codes(self.battle['right'],
                                    convert_from="name",
                                    convert_to="symbol"),
        }
        self.betting_tables = ('altcoin_bets', 'altcoin_bet_history',
                               'altcoin_vs_bets', 'altcoin_vs_bet_history')
        self.single_bet_amount = 5
        self.number_of_bets = 3

    def place_battle_bet(self, amount=None, denomination=None,
                         market=None, target=None):
        if amount is None:
            amount = self.single_bet_amount
        if denomination is None:
            denomination = self.denomination
        if market is None:
            market = self.battle
        if target is None:
            target = 'left'
        signal, data = self.socket_emit_receive({
            'emit-name': 'battle-bet',
            'amount': amount,
            'denomination': denomination,
            'left': market['left'],
            'right': market['right'],
            'target': market[target],
        })
        self.assertEqual(signal, 'battle-bet-response')
        self.assertTrue(data['success'])
        return signal, data

    def delete_battle_bets(self):
        delete_bet_query = "DELETE FROM altcoin_vs_bets WHERE better = %s"
        with cursor_context() as cur:
            cur.execute(delete_bet_query, (self.username,))
            return cur.rowcount

    def test_get_current_prices_battle(self):
        """get-current-prices"""
        for side in ('left', 'right'):
            intake = {
                'emit-name': 'get-current-prices',
                'coin': self.battle[side],
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
        """get-dyff-balance"""
        intake = {'emit-name': 'get-dyff-balance'}
        signal, data = self.socket_emit_receive(intake)
        self.assertEqual(signal, 'dyff-balance')
        self.assertEqual(data['balance'], 100)

    def test_get_time_remaining(self):
        """get-time-remaining"""
        intake = {'emit-name': 'get-time-remaining'}
        signal, data = self.socket_emit_receive(intake)
        self.assertEqual(signal, 'time-remaining')
        self.assertEqual(type(data['time_remaining']), str)
        minutes, seconds = map(int, data['time_remaining'].split(':'))
        self.assertTrue(0 <= minutes <= 60)
        self.assertTrue(0 <= seconds <= 60)

    def test_battle_bets(self):
        """battle-bets"""
        intake = {
            'emit-name': 'battle-bets',
            'left': self.battle['left'],
            'right': self.battle['right'],
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

    def test_battle_bet_right(self):
        """battle-bet (right)"""
        self.battle_bet('right')

    def test_battle_bet_left(self):
        """battle-bet (left)"""
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
                    'left': self.battle['left'],
                    'right': self.battle['right'],
                    'target': self.battle[target],
                }
                signal, data = self.socket_emit_receive(intake)
                self.assertEqual(signal, 'battle-bet-response')
                self.assertTrue(data['success'])
                self.assertIsNotNone(data['time_of_bet'])
                self.assertEqual(type(data['time_of_bet']), str)
                self.assertEqual(data['left_coin'],
                                 self.battle['left'])
                self.assertEqual(data['right_coin'],
                                 self.battle['right'])
                self.assertEqual(data['denomination'],
                                 self.denomination)
                self.assertEqual(data['bet_target'],
                                 currency_codes(self.battle[target],
                                                convert_from="name",
                                                convert_to="symbol"))
                query = (
                    "SELECT better, amount, denomination, bet_target "
                    "FROM %s WHERE better = %%s"
                )
                for table in ('altcoin_vs_bets', 'altcoin_vs_bet_history'):
                    stored_bet = None
                    with cursor_context(True) as cur:
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
                                     currency_codes(self.battle[target],
                                                convert_from="name",
                                                convert_to="symbol"))

    def tearDown(self):
        delete_query = "DELETE FROM %s WHERE better = %%s"
        reset_dyffs_query = (
            "UPDATE dyffs SET balance = 100 WHERE username = %s"
        )
        select_dyffs_query = "SELECT balance FROM dyffs WHERE username = %s"
        with cursor_context() as cur:
            for table in self.tables:
                cur.execute(delete_query % table, (self.username,))
            cur.execute(reset_dyffs_query, (self.username,))
            cur.execute(select_dyffs_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 100)

if __name__ == '__main__':
    unittest.main()
