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

from decimal import Decimal
from utils import *

from dyffy import app
from dyffy.models import db, User, Game, Bet

sketch = """
Game map:

    [spectate] --enter--> [lobby] --play--> [ingame] --gameover--> [spectate]
        |          |       |    ^                    
     cashout--> [stats]    -bet-|                    
"""

class Jellybeans(object):
    
    def __init__(self, user_id, min_players=3, game_minutes=10):

        self.game = Game.query.filter(Game.players.like('%' + str(user_id) + '%')).filter_by(finished=None).first()

        if not self.game:

            self.game = Game.query.filter_by(started=None, finished=None).first()

            if not self.game:

                soundcloud_id = 38422945

                self.game = Game(min_players=min_players, game_minutes=game_minutes, soundcloud_id=soundcloud_id)
                db.session.add(self.game)
                db.session.commit()

                self.game.add_player(user_id)



    def bet(self, user_id, guess, bet=10):

        self.game.add_bet(user_id=user_id, guess=guess, bet=bet)

        if len(self.game.bets) >= self.game.min_players:

            self.game.start()

