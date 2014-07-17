import sys, os, platform
import unittest
from decimal import *
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))
import settlement as s
from base_test import BaseTest
import config

class TestSettle(BaseTest):

    def setUp(self):
        BaseTest.setUp(self)

    def test_neutral(self):
        """settle.neutral: check whether change is approximately zero"""
        self.assertEqual(config.NEUTRAL_THRESHOLD, 1e-07)
        self.assertTrue(s.neutral(1e-08))
        self.assertTrue(s.neutral(0))
        self.assertTrue(s.neutral(Decimal(1e-08)))
        self.assertFalse(s.neutral(1e-06))
        self.assertFalse(s.neutral(0.00001))
        self.assertFalse(s.neutral(Decimal(0.001)))

    def test_return_bets(self):
        """
        settle.return_bets: return all bets to users who made them
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

    def _test_winners_losers_battle(self):
        """utils.winners_losers"""
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

    def _test_bet_counts_battle(self):
        """utils.bet_counts"""
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

    def _test_bets_exist_battle(self):
        """utils.bets_exist"""
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

    def _test_collect_pools_battle(self):
        """utils.collect_pools"""
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

    def _test_pool_disburse_battle(self):
        """utils.pool_disburse"""
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

    def _test_reset_bet_tables(self):
        """utils.reset_bet_tables"""
        if config.DEBUG:
            self.place_predict_bet(direction='+')
            self.place_predict_bet(direction='-')
            self.place_battle_bet(target='left')
            self.place_battle_bet(target='right')
            bets_reset = reset_bet_tables()
            self.assertEqual(type(bets_reset), int)
            self.assertGreater(bets_reset, 0)
            self.assertEqual(bets_reset, 4)
            with cursor_context() as cur:
                for table in config.BET_TABLES:
                    cur.execute("SELECT count(*) FROM %s" % table)
                    self.assertEqual(cur.fetchone()[0], 0)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()