#!/usr/bin/env python
"""
dyffy's super sweet game engine
"""
import datetime

from decimal import Decimal

from dyffy import app
from dyffy.models import db, User, Game, Bet, SoundCloud


class Jellybeans(object):
    
    def __init__(self, user_id, min_players=1, game_minutes=1):

        self.name = 'soundcloud'
        self.game = Game.query.filter(Game.players.any(id=user_id)).filter_by(finished=None).first()

        SoundCloud.update()
        track = SoundCloud.get_random_track()

        if not self.game:

            self.game = Game.query.filter_by(started=None, finished=None).first()

            if not self.game:

                SoundCloud.update()
                track = SoundCloud.get_random_track()
                soundcloud_id = track["id"]

                self.game = Game(
                    min_players = min_players,
                    game_minutes = game_minutes,
                    soundcloud_id = soundcloud_id,
                    name = self.name
                )
                db.session.add(self.game)
                db.session.commit()

                self.game.add_player(User.query.get(user_id))

        if self.game:
            self.game.current_time = datetime.datetime.now()



    def bet(self, user_id, guess, bet=10):

        self.game.add_bet(user_id=user_id, guess=guess, bet=bet)

        if len(self.game.bets) >= self.game.min_players:

            self.game.start()
