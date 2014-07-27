#!/usr/bin/env python
"""
dyffy's super sweet game engine
"""

import datetime
from decimal import Decimal

from dyffy import app
from dyffy.models import db, User, Game, Bet, SoundCloud


class Jellybeans(object):
    
    def __init__(self, user, min_players=3, game_minutes=1, name='soundcloud', soundcloud_id=None, game_id=None):

        self.game = None
        self.current_time = datetime.datetime.now()
        self.name = name
        self.game_minutes = game_minutes
        self.soundcloud_id = soundcloud_id
        self.min_players = min_players
        self.user = user

        if game_id:

            self.game = Game.query.get(game_id)

        else:

            # look for already open game that hasn't started
            self.game = Game.query.filter_by(started=None, finished=None).first()

        if self.game:

            self.soundcloud_id = self.game.stats.get('soundcloud_id')

        else:

            # grab a fresh soundcloud track
            SoundCloud.update()
            track = SoundCloud.get_random_track()

            self.soundcloud_id = track['id']

            self.game = Game(
                self.name,
                min_players = self.min_players,
                game_minutes = self.game_minutes
            )
            self.game.stats = {'soundcloud_id': self.soundcloud_id}

            db.session.add(self.game)
            db.session.commit()

    def bet(self, guess, bet=10):

        # add player and bet
        self.game.add_player(self.user)
        self.game.add_bet(user_id=self.user.id, guess=guess, bet=bet)

        if len(self.game.bets) >= self.game.min_players:

             self.start()

    def start(self):

        # execute model's start method
        self.game.start(on_finish=self.finish)

        # get current track count
        track = SoundCloud.get_track(self.game.stats['soundcloud_id'])
        self.game.stats['track'] = track

        db.session.commit()

    def finish(self):

        # execute model's finish method
        self.game.finish()

        # get actual number of playbacks + favorites
        track = SoundCloud.get_track(self.game.stats['soundcloud_id'])
        actual = track['playbacks']

        # calculate winner + how much they won
        bets = Bet.query.filter(Bet.game_id == self.game.id).all()
        diff = []
        total_amount_bet = Decimal("0")
        for b in bets:
            diff.append(abs(float(b.guess) - actual))
            total_amount_bet += b.amount
            b.amount = 0
        
        best_guess = diff.index(min(diff))
        winner_id = bets[best_guess].user_id
        winner = User.query.get(winner_id)
        winnings = total_amount_bet

        winner.wallet.dyf_balance += winnings

        self.game.stats['track'].update({'ending_playbacks': actual})
        self.game.stats['winner_id'] = winner.id
        self.game.stats['winner_username'] = winner.username
        self.game.stats['winnings'] = str(winnings)

        db.session.add(self.game)
        db.session.commit()
           
