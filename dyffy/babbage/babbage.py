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
import threading
import datetime
import account
import currency
from fysom import Fysom
from decimal import Decimal
from utils import *

from dyffy import app
from dyffy.models import db, User, Game, Bet, BetHistory


sketch = """
Game map:

    [spectate] --enter--> [lobby] --play--> [ingame] --gameover--> [spectate]
        |          |       |    ^                    
     cashout--> [stats]    -bet-|                    
"""

class Jellybeans(object):
    
    def __init__(self, min_players=3, game_minutes=10, user_id=None):

        self.game = Game.query.filter(db.table.column.ilike(str(user_id)).filter_by(finished=None).first()

        if not game:

            self.game = Game(min_players=min_players, game_minutes=game_minutes)

            self.game.add_player(user_id)

        return self.game


    def bet(self, user_id, guess, bet=10):

        self.game.add_bet(user_id=user_id, guess=guess, amount=bet)

        if len(self.game.bets) >= self.game.min_players:

            self.game.start()

