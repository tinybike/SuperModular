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
from fysom import Fysom
from decimal import Decimal
from utils import *
import callback
import db
import config

db.init()

sketch = """
Game map:

    [spectate] --enter--> [options] --play--> [ingame] --gameover--> [spectate]
        |          |                           |    ^
     cashout--> [stats]                        -bet-|
"""

game = Fysom({
    "initial": "spectate",
    "events": [{
        "name": "enter",
        "src": ["spectate", "stats"],
        "dst": "options",
    }, {
        "name": "cashout",
        "src": "spectate",
        "dst": "stats",
    }, {
        "name": "play",
        "src": "options",
        "dst": "ingame",
    }, {
        "name": "bet",
        "src": "ingame",
        "dst": "ingame",
    }, {
        "name": "gameover",
        "src": "ingame",
        "dst": "spectate",
    }],
    "callbacks": {
        "onenter": callback.enter_game,
        "onplay": callback.play_game,
        "onbet": callback.bet,
        "ongameover": callback.settle_bets,
        "onchangestate": callback.echo_timestamp,
    },
})

if __name__ == '__main__':
    config.DEBUG = True
    print sketch
    game.enter(user_id="4", title="soundcloud")
    game.play(user_id="4", title="soundcloud", genre="punk")
    game.bet(user_id="4",
             target="r",
             red="song1",
             blue="song2",
             amount=Decimal("0.2"),
             currency="DYF")
    game.gameover()
    game.cashout()
    db.session.close()
    print
