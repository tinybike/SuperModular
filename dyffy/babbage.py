#!/usr/bin/env python

import datetime, random
from decimal import Decimal

from dyffy import app
from dyffy import socketio

from dyffy.models import db, User, Game, Bet, SoundCloud


class Parimutuel(Game):

    def __init__(self):

        self.duration = 1
        self.name = 'parimutuel-dice'

        # look for already open game that hasn't finished
        current_game = Game.query.filter_by(finished=None).first()

        if current_game:

            self = current_game

        else:

            super(Parimutuel, self).__init__(self.name, rules={'duration': self.duration})

            db.session.add(self)
            db.session.commit()


    def bet(self, user, guess, amount):

        # add player and bet
        self.add_player(user)
        self.add_bet(user_id=user.id, guess=guess, amount=amount)

        if not self.started:

            self.start()

        return guess, amount

    def start(self):

        super(Parimutuel, self).start(on_finish=self.finish)
        db.session.commit()

    def finish(self):

        super(Parimutuel, self).finish()

        result = random.randint(1, 6)

        bets = Bet.query.filter(Bet.game_id == self.id).all()

        total_amount_bet = Decimal("0")
        winners = []
        pools = [0, 0, 0, 0, 0, 0]

        for b in bets:

            guess = int(b.guess)

            total_amount_bet += b.amount
            pools[guess-1] += b.amount

            if guess == result:

                winners.append({
                    'user_id': b.user_id,
                    'amount': b.amount
                })

        if pools[result - 1]:
            win_ratio = total_amount_bet / pools[result - 1]
        
        self.stats['winners'] = []

        for w in winners:

            winner = User.query.get(w['user_id'])
            self.stats['winners'].append({
                'id': winner.id,
                'username': winner.username
            })
            winner.wallet.dyf_balance += w['amount'] * win_ratio

        self.stats['result'] = result

        db.session.add(self)
        db.session.commit()

        # broadcast game-over
        socketio.emit('game-over', {'id': self.id, 'stats': self.stats }, namespace='/socket.io/')





class Jellybeans(Game):
    
    def __init__(self, soundcloud_id=None):

        self.name = 'soundcloud'
        self.game_minutes = 1
        self.soundcloud_id = soundcloud_id
        self.min_players = 3

        # look for already open game that hasn't started
        current_game = Game.query.filter_by(started=None, finished=None).first()

        if current_game:

            self = current_game

        else:

            super(Jellybeans, self).__init__(self.name, rules={'duration': self.duration, 'min_players': self.min_players})

            # grab a fresh soundcloud track
            SoundCloud.update()
            track = SoundCloud.get_random_track()

            self.soundcloud_id = track['id']
            self.stats = {'soundcloud_id': self.soundcloud_id}

            db.session.add(self)
            db.session.commit()

    def bet(self, user, guess, amount):

        amount = 10
        # add player and bet
        self.game.add_player(user)
        self.game.add_bet(user_id=user.id, guess=guess, amount=amount)

        if len(self.game.bets) >= self.game.rules['min_players']:

             self.start()

        return guess, amount

    def start(self):

        super(Parimutuel, self).start(on_finish=self.finish)

        self.no_more_bets = True

        # get current track count
        track = SoundCloud.get_track(self.game.stats['soundcloud_id'])
        self.stats['track'] = track

        db.session.commit()

    def finish(self):

        super(Parimutuel, self).finish()

        # get actual number of playbacks + favorites
        track = SoundCloud.get_track(self.stats['soundcloud_id'])
        actual = track['playbacks']

        # calculate winner + how much they won
        bets = Bet.query.filter(Bet.game_id == self.id).all()
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
        self.game.stats['winners'] = [{
            'user_id': winner.id,
            'username': winner.username,
            'winnings': str(winnings)
        }]

        db.session.add(self)
        db.session.commit()

        # broadcast game-over
        socketio.emit('game-over', {'id': self.id, 'stats': self.stats }, namespace='/socket.io/')

           
