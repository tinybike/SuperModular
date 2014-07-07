import platform
from flask import session, request, escape
from dyffy.utils import *
from dyffy import app, db, socketio
from decimal import *
import unittest
from socket_test import SocketTest

class TestUtils(SocketTest):
    """
    Tests for the utility functions non-trivial enough to need tests
    """
    def setUp(self):
        SocketTest.setUp(self)
        self.bet_amounts = [Decimal(bet).quantize(Decimal('.00000001'), \
            rounding=ROUND_HALF_EVEN) for bet in (0.01, 0.1, 1, 10)]
        self.denomination = 'DYF'
        self.awards = []
        self.award_categories = ('friends', 'chat', 'trading', 'scribble')
        self.currencies = {}
        select_awards_query = (
            "SELECT award_id, number_of_winners FROM awards ORDER BY award_id"
        )
        self.initial_winners = {}
        with db.cursor_context(True) as cur:
            cur.execute(select_awards_query)
            for row in cur:
                self.initial_winners[row['award_id']] = \
                    row['number_of_winners']
        self.predict_market = 'Bitcoin'
        self.battle_coin = {'left': 'Dogecoin', 'right': 'Bitcoin'}
        self.predict_symbol = currency_codes(self.predict_market,
                                             convert_from="name",
                                             convert_to="symbol")
        self.battle_symbol = {
            'left': currency_codes(self.battle_coin['left'],
                                   convert_from="name",
                                   convert_to="symbol"),
            'right': currency_codes(self.battle_coin['right'],
                                    convert_from="name",
                                    convert_to="symbol"),
        }
        self.betting_tables = ('altcoin_bets', 'altcoin_bet_history',
                               'altcoin_vs_bets', 'altcoin_vs_bet_history')
        self.single_bet_amount = 5
        self.number_of_bets = 3

    def place_predict_bet(self, amount=None, denomination=None,
                          market=None, direction=None):
        """Create bet in the prediction market"""
        if amount is None:
            amount = self.single_bet_amount
        if denomination is None:
            denomination = self.denomination
        if market is None:
            market = self.predict_market
        if direction is None:
            direction = '+'
        signal, data = self.socket_emit_receive({
            'emit-name': 'predict-bet',
            'amount': amount,
            'denomination': denomination,
            'market': market,
            'direction': direction,
        })
        self.assertEqual(signal, 'predict-bet-response')
        self.assertTrue(data['success'])
        return signal, data

    def place_battle_bet(self, amount=None, denomination=None,
                         market=None, target=None):
        if amount is None:
            amount = self.single_bet_amount
        if denomination is None:
            denomination = self.denomination
        if market is None:
            market = self.battle_coin
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

    def delete_predict_bets(self):    
        delete_bet_query = "DELETE FROM altcoin_bets WHERE better = %s"
        with db.cursor_context() as cur:
            cur.execute(delete_bet_query, (self.username,))
            return cur.rowcount

    def delete_battle_bets(self):
        delete_bet_query = "DELETE FROM altcoin_vs_bets WHERE better = %s"
        with db.cursor_context() as cur:
            cur.execute(delete_bet_query, (self.username,))
            return cur.rowcount

    def test_currency_precision(self):
        """utils.currency_precision"""
        with db.cursor_context(True) as cur:
            cur.execute("SELECT symbol, name FROM currencies LIMIT 25")
            for row in cur:
                self.currencies[row['symbol']] = row['name']
        for symbol in self.currencies:
            if symbol == 'NXT':
                self.assertEqual(currency_precision(symbol), '.01')
            elif symbol == 'XRP':
                self.assertEqual(currency_precision(symbol), '.000001')
            else:
                self.assertEqual(currency_precision(symbol), '.00000001')        

    def test_currency_codes(self):
        """utils.currency_codes: convert between currency symbols and names"""
        with db.cursor_context(True) as cur:
            cur.execute("SELECT symbol, name FROM currencies LIMIT 25")
            for row in cur:
                self.currencies[row['symbol']] = row['name']
        for symbol, name in self.currencies.items():
            self.assertEqual(currency_codes(symbol), name)
            self.assertEqual(currency_codes(name, convert_from='name',
                                            convert_to='symbol'), symbol)

    def test_debit(self):
        """utils.debit: debit funds from user account"""
        with self.login():
            balance_query = "SELECT balance FROM dyffs WHERE username = %s"
            for i, amount in enumerate(self.bet_amounts):
                balance = None
                with db.cursor_context() as cur:
                    cur.execute(balance_query, (self.username,))
                    self.assertEqual(cur.rowcount, 1)
                    balance = cur.fetchone()[0]
                self.assertIsNotNone(balance)
                if i == 0:
                    self.assertEqual(balance, 100)
                new_balance = debit(self.username, amount, self.denomination)
                self.assertTrue(new_balance is not False)
                self.assertEqual(new_balance, balance - amount)
                new_stored_balance = None
                with db.cursor_context() as cur:
                    cur.execute(balance_query, (self.username,))
                    self.assertEqual(cur.rowcount, 1)
                    new_stored_balance = cur.fetchone()[0]
                self.assertIsNotNone(new_stored_balance)
                self.assertEqual(new_stored_balance, new_balance)

    def test_update_awards(self):
        """utils.update_awards: update award tables"""
        initial_state = {}
        with db.cursor_context(True) as cur:
            initial_state_query = (
                "SELECT award_id, number_of_winners FROM awards"
            )
            cur.execute(initial_state_query)
            for row in cur:
                initial_state[row['award_id']] = row['number_of_winners']
        with self.login():
            for category in self.award_categories:
                counter = 0
                while True:
                    counter += 1
                    next_award = None
                    updates = update_awards(category,
                                            user_ids=[session['user_id']])
                    with db.cursor_context() as cur:
                        tracking_query = (
                            "SELECT number_completed FROM award_tracking "
                            "WHERE user_id = %s AND category = %s"
                        )
                        cur.execute(tracking_query, (self.user_id, category))
                        self.assertEqual(cur.rowcount, 1)
                        number_completed = cur.fetchone()[0]
                        self.assertEqual(number_completed, counter)
                        next_award_query = (
                            "SELECT requirement, award_id, award_name "
                            "FROM awards "
                            "WHERE category = %s AND requirement >= %s "
                            "ORDER BY requirement LIMIT 1"
                        )
                        cur.execute(next_award_query, (category,
                                                       number_completed))
                        if cur.rowcount:
                            results = cur.fetchone()
                            next_award = {
                                'requirement': int(results[0]),
                                'award_id': results[1],
                                'award_name': results[2],
                            }
                            if next_award['requirement'] == number_completed:
                                win_category = None
                                select_winner_query = (
                                    "SELECT award_id, category "
                                    "FROM award_winners "
                                    "WHERE user_id = %s "
                                    "ORDER BY won_on DESC LIMIT 1"
                                )
                                cur.execute(select_winner_query,
                                            (self.user_id,))
                                for row in cur:
                                    award_id = row[0]
                                    win_category = row[1]
                                self.assertIsNotNone(win_category)
                                self.assertEqual(category, win_category)
                                select_number_of_winners_query = (
                                    "SELECT number_of_winners FROM awards "
                                    "WHERE award_id = %s"
                                )
                                cur.execute(select_number_of_winners_query,
                                            (award_id,))
                                self.assertEqual(cur.rowcount, 1)
                                number_of_winners = cur.fetchone()[0]
                                self.assertEqual(number_of_winners,
                                                 initial_state[award_id]+1)
                                self.awards.append(award_id)
                        else:
                            break

    def test_check_interval(self):
        """utils.check_interval: get betting round's time remaining"""
        time_remaining = check_interval()
        self.assertEqual(type(time_remaining), str)
        split_time_remaining = time_remaining.split(':')
        self.assertEqual(len(split_time_remaining), 2)
        self.assertEqual(len(split_time_remaining[0]), 2)
        self.assertEqual(len(split_time_remaining[1]), 2)
        time_remaining = check_interval(startup=True)
        self.assertEqual(type(time_remaining), int)
        self.assertTrue(0 <= time_remaining <= 3600)

    def test_final_coin_prices(self):
        """utils.final_coin_prices: coin prices at round closing"""
        fields = ('price', 'start_price', 'data_source', 'coin_code', 'coin')
        for coin_data in final_coin_prices():
            for field in fields:
                self.assertIn(field, coin_data)
            self.assertEqual(type(coin_data['price']), Decimal)
            self.assertGreaterEqual(coin_data['price'], 0)
            self.assertEqual(type(coin_data['start_price']), Decimal)
            self.assertGreaterEqual(coin_data['start_price'], 0)
            self.assertEqual(type(coin_data['coin_code']), str)
            self.assertEqual(coin_data['coin_code'],
                             coin_data['coin_code'].upper())
            self.assertEqual(type(coin_data['coin']), str)
            self.assertEqual(type(coin_data['data_source']), str)
            if coin_data['coin_code'] == 'BTC':
                self.assertEqual(coin_data['data_source'], 'BitcoinAverage')
            else:
                self.assertEqual(coin_data['data_source'], 'CryptoCoinCharts')

    def test_neutral(self):
        """utils.neutral: check whether change is approximately zero"""
        self.assertIn('NEUTRAL_THRESHOLD', app.config)
        self.assertEqual(app.config['NEUTRAL_THRESHOLD'], 1e-07)
        self.assertTrue(neutral(1e-08))
        self.assertTrue(neutral(0))
        self.assertTrue(neutral(Decimal(1e-08)))
        self.assertFalse(neutral(1e-06))
        self.assertFalse(neutral(0.00001))
        self.assertFalse(neutral(Decimal(0.001)))

    def test_return_bets_predict(self):
        """
        utils.return_bets: return all bets to users who made them (predict)
        """
        for direction in ('+', '-'):
            starting_dyffs = all_users_dyffs_balance()
            # Make a predict market bet
            signal, data = self.socket_emit_receive({
                'emit-name': 'predict-bet',
                'amount': self.single_bet_amount,
                'denomination': self.denomination,
                'market': self.predict_market,
                'direction': direction,
            })
            self.assertEqual(signal, 'predict-bet-response')
            self.assertTrue(data['success'])
            self.assertIsNotNone(data['time_of_bet'])
            self.assertEqual(type(data['time_of_bet']), str)
            # Return the bets
            bets_returned = return_bets(coin_code=self.predict_symbol)
            final_dyffs = all_users_dyffs_balance()
            self.assertDictEqual(starting_dyffs, final_dyffs)

    def test_return_bets_battle(self):
        """
        utils.return_bets: return all bets to users who made them (battle)
        """
        for target in ('left', 'right'):
            starting_dyffs = all_users_dyffs_balance()
            # Make a battle market bet
            signal, data = self.socket_emit_receive({
                'emit-name': 'battle-bet',
                'amount': self.single_bet_amount,
                'denomination': self.denomination,
                'left': self.battle_coin['left'],
                'right': self.battle_coin['right'],
                'target': self.battle_coin[target],
            })
            self.assertEqual(signal, 'battle-bet-response')
            self.assertTrue(data['success'])
            self.assertIsNotNone(data['time_of_bet'])
            self.assertEqual(type(data['time_of_bet']), str)
            self.assertEqual(data['left_coin'], self.battle_coin['left'])
            self.assertEqual(data['right_coin'], self.battle_coin['right'])
            self.assertEqual(data['denomination'], self.denomination)
            self.assertEqual(data['bet_target'], self.battle_symbol[target])
            # Return the bets
            return_bets(battle_coin=self.battle_symbol)
            final_dyffs = all_users_dyffs_balance()
            self.assertDictEqual(starting_dyffs, final_dyffs)

    def test_user_dyffs_balance(self):
        """utils.user_dyffs_balance"""
        balance = user_dyffs_balance(self.username)
        self.assertIsNotNone(balance)
        self.assertEqual(type(balance), Decimal)
        self.assertEqual(balance, self.dyffs_default_balance)

    def test_all_users_dyffs_balance(self):
        """utils.all_users_dyffs_balance"""
        balance = all_users_dyffs_balance()
        self.assertIsNotNone(balance)
        self.assertEqual(type(balance), dict)
        for usr, bal in balance.items():
            self.assertEqual(type(usr), str)
            self.assertEqual(type(bal), Decimal)
        self.assertEqual(balance[self.username], self.dyffs_default_balance)

    def test_winners_losers_predict(self):
        """utils.winners_losers (predict)"""
        for winning_bet in ('+', '-'):
            losing_bet = '-' if winning_bet == '+' else '+'
            # Place winning bet
            signal, data = self.place_predict_bet(direction=winning_bet)
            roster = winners_losers(winning_bet, self.predict_symbol)
            self.assertIn('win', roster)
            self.assertIn('loss', roster)
            self.assertEqual(len(roster['win']), 1)
            self.assertEqual(type(roster['win'][0][0]), str)
            self.assertEqual(type(roster['win'][0][1]), Decimal)
            self.assertEqual(type(roster['win'][0][2]), str)
            self.assertEqual(roster['win'][0][0], self.username)
            self.assertEqual(roster['win'][0][1], self.single_bet_amount)
            self.assertEqual(roster['win'][0][2], self.denomination)
            self.assertEqual(len(roster['loss']), 0)
            self.assertEqual(self.delete_predict_bets(), 1)
            # Place losing bet
            signal, data = self.place_predict_bet(direction=losing_bet)
            roster = winners_losers(winning_bet, self.predict_symbol)
            self.assertIn('win', roster)
            self.assertIn('loss', roster)
            self.assertEqual(len(roster['loss']), 1)
            self.assertEqual(type(roster['loss'][0][0]), str)
            self.assertEqual(type(roster['loss'][0][1]), Decimal)
            self.assertEqual(type(roster['loss'][0][2]), str)
            self.assertEqual(roster['loss'][0][0], self.username)
            self.assertEqual(roster['loss'][0][1], self.single_bet_amount)
            self.assertEqual(roster['loss'][0][2], self.denomination)
            self.assertEqual(len(roster['win']), 0)
            self.assertEqual(self.delete_predict_bets(), 1)

    def test_winners_losers_battle(self):
        """utils.winners_losers (battle)"""
        for winning_bet in ('left', 'right'):
            losing_bet = 'right' if winning_bet == 'left' else 'left'
            # Place winning bet
            signal, data = self.place_battle_bet(target=winning_bet)
            roster = winners_losers(winning_bet, self.battle_symbol,
                                    market_type='battle')
            self.assertIn('win', roster)
            self.assertIn('loss', roster)
            self.assertEqual(len(roster['win']), 1)
            self.assertEqual(type(roster['win'][0][0]), str)
            self.assertEqual(type(roster['win'][0][1]), Decimal)
            self.assertEqual(type(roster['win'][0][2]), str)
            self.assertEqual(roster['win'][0][0], self.username)
            self.assertEqual(roster['win'][0][1], self.single_bet_amount)
            self.assertEqual(roster['win'][0][2], self.denomination)
            self.assertEqual(len(roster['loss']), 0)
            self.assertEqual(self.delete_battle_bets(), 1)
            # Place losing bet
            signal, data = self.place_battle_bet(target=losing_bet)
            roster = winners_losers(winning_bet, self.battle_symbol,
                                    market_type='battle')
            self.assertIn('win', roster)
            self.assertIn('loss', roster)
            self.assertEqual(len(roster['loss']), 1)
            self.assertEqual(type(roster['loss'][0][0]), str)
            self.assertEqual(type(roster['loss'][0][1]), Decimal)
            self.assertEqual(type(roster['loss'][0][2]), str)
            self.assertEqual(roster['loss'][0][0], self.username)
            self.assertEqual(roster['loss'][0][1], self.single_bet_amount)
            self.assertEqual(roster['loss'][0][2], self.denomination)
            self.assertEqual(len(roster['win']), 0)
            self.assertEqual(self.delete_battle_bets(), 1)

    def test_bet_counts_predict(self):
        """utils.bet_counts (predict)"""
        for direction in ('+', '-'):
            for i in xrange(self.number_of_bets):
                signal, data = self.place_predict_bet(direction=direction)
                bet_count = bet_counts(self.predict_symbol)
                self.assertIn('+', bet_count)
                self.assertIn('-', bet_count)
                self.assertEqual(type(bet_count['+']), long)
                self.assertEqual(type(bet_count['-']), long)
                self.assertEqual(bet_count[direction], 1L)
                if direction == '+':
                    self.assertEqual(bet_count['-'], 0L)
                else:
                    self.assertEqual(bet_count['+'], 1L)

    def test_bet_counts_battle(self):
        """utils.bet_counts (battle)"""
        for target in ('left', 'right'):
            for i in xrange(self.number_of_bets):
                signal, data = self.place_battle_bet(target=target)
                bet_count = bet_counts(self.battle_symbol,
                                       market_type='battle')
                self.assertIn('left', bet_count)
                self.assertIn('right', bet_count)
                self.assertEqual(type(bet_count['left']), long)
                self.assertEqual(type(bet_count['right']), long)
                self.assertEqual(bet_count[target], 1L)
                if target == 'left':
                    self.assertEqual(bet_count['right'], 0L)
                else:
                    self.assertEqual(bet_count['left'], 1L)

    def test_bets_exist_predict(self):
        """utils.bets_exist (predict)"""
        for direction in ('+', '-'):
            exists = bets_exist(self.predict_symbol)
            self.assertEqual(type(exists), bool)
            self.assertFalse(exists)
            for i in xrange(self.number_of_bets):
                signal, data = self.place_predict_bet(direction=direction)
                exists = bets_exist(self.predict_symbol)
                self.assertEqual(type(exists), bool)
                if direction == '-':
                    self.assertTrue(exists)
                else:
                    self.assertFalse(exists)

    def test_bets_exist_battle(self):
        """utils.bets_exist (battle)"""
        for target in ('left', 'right'):
            exists = bets_exist(self.battle_symbol,
                                market_type='battle')
            self.assertEqual(type(exists), bool)
            self.assertFalse(exists)
            for i in xrange(self.number_of_bets):
                signal, data = self.place_battle_bet(target=target)
                exists = bets_exist(self.battle_symbol,
                                    market_type='battle')
                self.assertEqual(type(exists), bool)
                if target == 'right':
                    self.assertTrue(exists)
                else:
                    self.assertFalse(exists)

    def test_collect_pools_predict(self):
        """utils.collect_pools (predict)"""
        for winning_bet in ('+', '-'):
            losing_bet = '-' if winning_bet == '+' else '+'
            # Place winning bets
            for i in xrange(self.number_of_bets):
                signal, data = self.place_predict_bet(direction=winning_bet)
                roster = winners_losers(winning_bet, self.predict_symbol)
                pools = collect_pools(roster)
                self.assertIn('win', pools)
                self.assertIn('loss', pools)
                self.assertEqual(type(pools['win']), Decimal)
                self.assertEqual(type(pools['loss']), Decimal)
                self.assertEqual(pools['win'], self.single_bet_amount*(i+1))
                self.assertEqual(pools['loss'], 0)
            self.assertEqual(self.delete_predict_bets(), 1)
            # Place losing bets
            for i in xrange(self.number_of_bets):
                signal, data = self.place_predict_bet(direction=losing_bet)
                roster = winners_losers(winning_bet, self.predict_symbol)
                pools = collect_pools(roster)
                self.assertIn('win', pools)
                self.assertIn('loss', pools)
                self.assertEqual(type(pools['win']), Decimal)
                self.assertEqual(type(pools['loss']), Decimal)
                self.assertEqual(pools['win'], 0)
                self.assertEqual(pools['loss'], self.single_bet_amount*(i+1))
            self.assertEqual(self.delete_predict_bets(), 1)

    def test_collect_pools_battle(self):
        """utils.collect_pools (battle)"""
        for winning_bet in ('left', 'right'):
            losing_bet = 'right' if winning_bet == 'left' else 'left'
            # Place winning bets
            for i in xrange(self.number_of_bets):
                signal, data = self.place_battle_bet(target=winning_bet)
                roster = winners_losers(winning_bet, self.battle_symbol,
                                        market_type='battle')
                pools = collect_pools(roster)
                self.assertIn('win', pools)
                self.assertIn('loss', pools)
                self.assertEqual(type(pools['win']), Decimal)
                self.assertEqual(type(pools['loss']), Decimal)
                self.assertEqual(pools['win'], self.single_bet_amount*(i+1))
                self.assertEqual(pools['loss'], 0)
            self.assertEqual(self.delete_battle_bets(), 1)
            # Place losing bets
            for i in xrange(self.number_of_bets):
                signal, data = self.place_battle_bet(target=losing_bet)
                roster = winners_losers(winning_bet, self.battle_symbol,
                                        market_type='battle')
                pools = collect_pools(roster)
                self.assertIn('win', pools)
                self.assertIn('loss', pools)
                self.assertEqual(type(pools['win']), Decimal)
                self.assertEqual(type(pools['loss']), Decimal)
                self.assertEqual(pools['win'], 0)
                self.assertEqual(pools['loss'], self.single_bet_amount*(i+1))
            self.assertEqual(self.delete_battle_bets(), 1)

    def test_pool_disburse_predict(self):
        """utils.pool_disburse (predict)"""
        for winning_bet in ('+', '-'):
            losing_bet = '-' if winning_bet == '+' else '+'
            # Place winning bet(s)
            for i in xrange(self.number_of_bets):
                signal, data = self.place_predict_bet(direction=winning_bet)
                roster = winners_losers(winning_bet, self.predict_symbol)
                pools = collect_pools(roster)
                winnings, losses = pool_disburse(roster, pools)
                self.assertEqual(type(winnings), dict)
                self.assertEqual(type(losses), dict)
                self.assertEqual(len(winnings), 1)
                self.assertEqual(len(losses), 0)
                self.assertIn(self.username, winnings)
                self.assertEqual(type(winnings[self.username]), Decimal)
                self.assertEqual(winnings[self.username], self.single_bet_amount*(i+1))
            self.assertEqual(self.delete_predict_bets(), 1)
            # Place losing bet(s)
            for i in xrange(self.number_of_bets):
                signal, data = self.place_predict_bet(direction=losing_bet)
                roster = winners_losers(winning_bet, self.predict_symbol)
                pools = collect_pools(roster)
                winnings, losses = pool_disburse(roster, pools)
                self.assertEqual(type(winnings), dict)
                self.assertEqual(type(losses), dict)
                self.assertEqual(len(winnings), 0)
                self.assertEqual(len(losses), 1)
                self.assertIn(self.username, losses)
                self.assertEqual(type(losses[self.username]), Decimal)
                self.assertEqual(losses[self.username], self.single_bet_amount*(i+1))
            self.assertEqual(self.delete_predict_bets(), 1)

    def test_pool_disburse_battle(self):
        """utils.pool_disburse (battle)"""
        for winning_bet in ('left', 'right'):
            losing_bet = 'right' if winning_bet == 'left' else 'left'
            # Place winning bets
            for i in xrange(self.number_of_bets):
                signal, data = self.place_battle_bet(target=winning_bet)
                roster = winners_losers(winning_bet, self.battle_symbol,
                                        market_type='battle')
                pools = collect_pools(roster)
                winnings, losses = pool_disburse(roster, pools)
                self.assertEqual(type(winnings), dict)
                self.assertEqual(type(losses), dict)
                self.assertEqual(len(winnings), 1)
                self.assertEqual(len(losses), 0)
                self.assertIn(self.username, winnings)
                self.assertEqual(type(winnings[self.username]), Decimal)
                self.assertEqual(winnings[self.username], self.single_bet_amount*(i+1))
            self.assertEqual(self.delete_battle_bets(), 1)
            # Place losing bet(s)
            for i in xrange(self.number_of_bets):
                signal, data = self.place_battle_bet(target=losing_bet)
                roster = winners_losers(winning_bet, self.battle_symbol,
                                        market_type='battle')
                pools = collect_pools(roster)
                winnings, losses = pool_disburse(roster, pools)
                self.assertEqual(type(winnings), dict)
                self.assertEqual(type(losses), dict)
                self.assertEqual(len(winnings), 0)
                self.assertEqual(len(losses), 1)
                self.assertIn(self.username, losses)
                self.assertEqual(type(losses[self.username]), Decimal)
                self.assertEqual(losses[self.username], self.single_bet_amount*(i+1))
            self.assertEqual(self.delete_battle_bets(), 1)

    def test_reset_bet_tables(self):
        """utils.reset_bet_tables"""
        if app.config['DEBUG']:
            self.place_predict_bet(direction='+')
            self.place_predict_bet(direction='-')
            self.place_battle_bet(target='left')
            self.place_battle_bet(target='right')
            bets_reset = reset_bet_tables()
            self.assertEqual(type(bets_reset), int)
            self.assertGreater(bets_reset, 0)
            self.assertEqual(bets_reset, 4)
            with db.cursor_context() as cur:
                for table in app.config['BET_TABLES']:
                    cur.execute("SELECT count(*) FROM %s" % table)
                    self.assertEqual(cur.fetchone()[0], 0)

    def test_round_complete(self):
        """utils.round_complete: close out betting markets"""
        if app.config['DEPLOY_ENV'] != 'prod':
            total_dyffs_query = "SELECT sum(balance) FROM dyffs"
            with db.cursor_context() as cur:
                cur.execute(total_dyffs_query)
                starting_total_dyffs = cur.fetchone()[0]
                self.assertEqual(type(starting_total_dyffs), Decimal)
                self.assertGreater(starting_total_dyffs, 0)
            with self.login():
                round_complete()
                altcoin_bet_queries = (
                    "SELECT count(*) FROM altcoin_bets",
                    "SELECT count(*) FROM altcoin_vs_bets",
                (
                    "SELECT count(*) FROM altcoin_current_round "
                    "WHERE price_change IS NOT NULL "
                    "OR end_price IS NOT NULL"
                ))
                with db.cursor_context() as cur:
                    for query in altcoin_bet_queries:
                        cur.execute(query)
                        self.assertEqual(cur.fetchone()[0], 0)
                    cur.execute(total_dyffs_query)
                    ending_total_dyffs = cur.fetchone()[0]
                    self.assertEqual(type(starting_total_dyffs), Decimal)
                    self.assertEqual(starting_total_dyffs, ending_total_d yffs)
        else:
            self.assertFalse(app.config['DEBUG'])
            self.assertEqual(platform.node(), 'loopy')

    def tearDown(self):
        delete_awards_queries = (
            "UPDATE award_tracking SET number_completed = 0 WHERE user_id = %s",
            "DELETE FROM award_winners WHERE user_id = %s",
        )
        with db.cursor_context() as cur:
            for query in delete_awards_queries:
                cur.execute(query, (self.user_id,))
            if self.awards:
                reset_winners_query = (
                    "UPDATE awards "
                    "SET number_of_winners = number_of_winners - 1 "
                    "WHERE award_id = %s "
                    "RETURNING number_of_winners"
                )
                count_winners_query = (
                    "SELECT number_of_winners FROM awards WHERE award_id = %s"
                )
                for award in self.awards:
                    cur.execute(reset_winners_query, (award,))
                    self.assertEqual(cur.rowcount, 1)
                    number_of_winners = cur.fetchone()[0]
                    cur.execute(count_winners_query, (award,))
                    self.assertEqual(cur.fetchone()[0], number_of_winners)
                    self.assertGreaterEqual(number_of_winners,
                                            self.initial_winners[award])
        select_awards_queries = ((
            "SELECT max(number_completed) FROM award_tracking "
            "WHERE user_id = %s"
        ),
            "SELECT count(*) FROM award_winners WHERE user_id = %s",
        )
        with db.cursor_context() as cur:
            for query in select_awards_queries:
                cur.execute(query, (self.user_id,))
                self.assertEqual(cur.fetchone()[0], 0)
        reset_dyffs_query = (
            "UPDATE dyffs SET balance = 100 WHERE username = %s"
        )
        select_dyffs_query = "SELECT balance FROM dyffs WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(reset_dyffs_query, (self.username,))
            cur.execute(select_dyffs_query, (self.username,))
            self.assertEqual(cur.fetchone()[0], 100)
        delete_query = "DELETE FROM %s WHERE better = %%s"
        with db.cursor_context() as cur:
            for table in self.betting_tables:
                cur.execute(delete_query % table, (self.username,))


if __name__ == '__main__':
    unittest.main()