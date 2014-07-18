#!/usr/bin/env python
"""
Babbage: dyffy's super sweet game engine
Usage:
    - Events are methods of the game object:
        from babbage import game
        game.enter(user_id="4", title="soundcloud")
        game.play(user_id="4", title="soundcloud", genre="punk")
@author jack@tinybike.net
"""
import datetime
from fysom import Fysom
from decimal import Decimal
from utils import *
import db
import config

db.init()

sketch = """
Game map:

    [spectate] --enter--> [lobby] --play--> [ingame] --gameover--> [spectate]
        |          |       |    ^                    
     cashout--> [stats]    -bet-|                    
"""

class Jellybeans(object):
    
    def __init__(self, min_players=3, game_minutes=10):
        self.min_players = min_players
        self.game_minutes = game_minutes
        self.num_players = 0
        self.num_bets = 0
        self.players = []
        self.title = "soundcloud"
        self.options = []
        self.game = Fysom({
            "initial": "spectate",
            "events": [{
                "name": "enter",
                "src": ["spectate", "stats"],
                "dst": "lobby",
            }, {
                "name": "cashout",
                "src": "spectate",
                "dst": "stats",
            }, {
                "name": "play",
                "src": "lobby",
                "dst": "ingame",
            }, {
                "name": "bet",
                "src": "lobby",
                "dst": "lobby",
            }, {
                "name": "gameover",
                "src": "ingame",
                "dst": "spectate",
            }],
            "callbacks": {
                "onenter": self.enter,
                "onplay": self.play,
                "onbet": self.bet,
                "ongameover": self.gameover,
                "onchangestate": self.changestate,
            },
        })
        self.started = False

    def enter(self, e):
        """Enter a game"""
        if config.DEBUG:
            print e.user_id, "enters the lobby"
        user_id = str(e.user_id)
        self.players.append({"user_id": user_id})
        self.num_players += 1

    def play(self, e):
        """Specify options and start the game"""
        if config.DEBUG:
            print self.players, "are now playing (" + e.options + ")"
        data.update(e)
        res = (db.session.query(Jellybeans)
                 .filter(Jellybeans.started==None,
                         Jellybeans.finished==None)
                 .limit(1)
                 .all())
        if res:
            res[0].started = datetime.datetime.now()
            db.session.commit()
            if config.DEBUG:
                print "Playing:", res[0].soundcloud_id

    def bet(self, e):
        """Record a bet in the bets table in the database"""
        if config.DEBUG:
            print e.user_id, "guesses", e.guess, ", betting", e.amount, e.currency
        if type(e.amount) != Decimal:
            precision = currency.get_precision(e.currency)
            amount = Decimal(e.amount).quantize(precision,
                                                rounding=ROUND_HALF_EVEN)
        else:
            amount = e.amount
        if account.debit(e.user_id, amount, e.currency,
                         session=db.session, handle_commit=False):
            res = db.session.query(Bet).filter(Bet.user_id==e.user_id,
                                               Bet.currency==e.currency,
                                               Bet.game=="Jellybeans").all()
            if res:
                res[0].amount += amount
            else:
                db.session.add(Bet(user_id=e.user_id,
                                   game="Jellybeans",
                                   guess=e.guess,
                                   amount=amount,
                                   currency="DYF"))
            self.num_bets += 1
            p = [player["user_id"] == e.user_id for player in self.players]
            idx = p.index(True)
            self.players[idx]["guess"] = e.guess
            self.players[idx]["bet"] = e.amount
            self.players[idx]["currency"] = e.currency
            db.session.commit()
        else:
            db.session.rollback()

    def gameover(self, e):
        """
        It's game over, man.  Game over!
        - If the result is neutral (~zero), return all bets
        - If either side has no betters, return all bets
        - Otherwise, decide winners/losers and determine payouts
        """
        # res.db.session.query(SoundCloudBattle)
        # outcome = settle.event_outcome()

        # if settle.neutral(price_change) or not settle.bets_exist(coin_data['coin_code']):
        #     settle.return_bets(coin_code=coin_data['coin_code'])
        
        # else:
        #     winning_direction = '+' if price_change > 0 else '-'
        #     roster = settle.winners_losers(winning_direction, coin_data['coin_code'])
        #     pools = settle.collect_pools(roster)
        #     winnings, losses = settle.pool_disburse(roster, pools)
        #     settle.store_round_results(winners, losers, winnings, losses)
        
        # settle.prepare_next_round(coin_data['price'], coin_data['coin_code'])
        # settle.reset_bet_tables()

    def changestate(self, e):
        timestamp = datetime.datetime.now()
        print "@%s: [%s] --%s--> [%s]" % (timestamp, e.src, e.event, e.dst)

    # Betting API methods
    # user_id --> API --> game object
    
    def add_player(self, user_id):
        self.game.enter(user_id)
        if self.num_bets >= self.min_players:
            self.game.play(options=self.options,
                           duration=self.game_minutes)

    def add_bet(self, user_id, guess, bet=10, currency="DYF"):
        self.game.bet(user_id=user_id,
                      guess=guess,
                      amount=bet,
                      currency=currency)

    def get_player(self, user_id):
        p = [player["user_id"] == e.user_id for player in self.players]
        return self.players[p.index(True)]

    def get_players(self):
        return self.players

if __name__ == '__main__':
    config.DEBUG = True
    print sketch
    jb = Jellybeans(min_players=3, game_minutes=10)
    jb.add_player("4")
    jb.add_player("3")
    jb.add_player("2")
    jb.game.gameover()
    jb.game.cashout()
    db.session.close()
    print
