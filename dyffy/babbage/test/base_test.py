import unittest
from decimal import *
from game import game
from models import Bet, BetHistory, Wallet, start_session
import config

class BaseTest(unittest.TestCase):

    def setUp(self):
        getcontext().prec = 28
        self.user_id = "4"
        self.game = game
        self.session = start_session()
        self.reset_wallet()
        self.reset_bets()

    def reset_wallet(self):
        res = self.session.query(Wallet).filter(Wallet.user_id==self.user_id).one()
        self.starting_dyf_balance = Decimal("100")
        res.dyf_balance = self.starting_dyf_balance
        self.session.commit()

    def reset_bets(self):
        res = self.session.query(Bet).filter(Bet.user_id==self.user_id).all()
        for r in res:
            self.session.delete(r)
        res = self.session.query(BetHistory).filter(BetHistory.user_id==self.user_id).all()
        for r in res:
            self.session.delete(r) 
        self.session.commit()

    def tearDown(self):
        self.reset_wallet()
        self.reset_bets()
        session.close()
