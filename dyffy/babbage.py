#!/usr/bin/env python

import datetime, random
from decimal import Decimal

from dyffy import app
from dyffy import socketio

from dyffy.models import db, User, Game, Bet, SoundCloud


class Parimutuel(Game):

    def __init__(self):

        self.name = 'parimutuel-dice'
        self.rules = {'duration': 1}

        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_game(cls):

        # look for already open game that hasn't finished
        current_game = cls.query.filter_by(finished=None, name=cls.name).first()

        if current_game:
            return current_game
        else:
            return cls()

    def bet(self, user, guess, amount):

        # add player and bet
        self.add_player(user)
        self.add_bet(user_id=user.id, guess=guess, amount=amount)

        if not self.started:

            self.start()

        return guess, amount  # send back guess and amout so we can control these within the game class

    def start(self):

        super(Parimutuel, self).start(on_finish=self.finish)

        db.session.add(self)
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
        
        self.data['winners'] = []

        for w in winners:

            winner = User.query.get(w['user_id'])
            self.data['winners'].append({
                'id': winner.id,
                'username': winner.username,
                'winnings': w.amount
            })
            winner.wallet.dyf_balance += w['amount'] * win_ratio

        self.data['result'] = result
        self.no_more_bets = True

        db.session.add(self)
        db.session.commit()

        # broadcast game-over
        socketio.emit('game-over', {'id': self.id, 'data': self.data }, namespace='/socket.io/')





class Jellybeans(Game):

    def __init__(self):

        self.name = 'soundcloud'

        # grab a fresh soundcloud track
        SoundCloud.update()
        track = SoundCloud.get_random_track()

        self.soundcloud_id = track['id']
        self.data = {'soundcloud_id': self.soundcloud_id}
        self.rules = {'duration': 1, 'min_players': 3}

        db.session.add(self)
        db.session.commit()

    @classmethod
    def find_game(cls):

        # look for already open game that hasn't finished
        current_game = cls.query.filter_by(finished=None, started=None, name=cls.name).first()

        if current_game:
            return current_game
        else:
            return cls()


    def bet(self, user, guess, amount):

        amount = 10

        # add player and bet
        self.add_player(user)
        self.add_bet(user_id=user.id, guess=guess, amount=amount)

        if len(self.bets) >= self.rules['min_players']:

             self.start()

        return guess, amount

    def start(self):

        super(Parimutuel, self).start(on_finish=self.finish)

        self.no_more_bets = True

        # get current track count
        track = SoundCloud.get_track(self.data['soundcloud_id'])
        self.data['track'] = track

        db.session.add(self)
        db.session.commit()

    def finish(self):

        super(Parimutuel, self).finish()

        # get actual number of playbacks + favorites
        track = SoundCloud.get_track(self.data['soundcloud_id'])
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

        self.data['track'].update({'ending_playbacks': actual})
        self.data['winners'] = [{
            'user_id': winner.id,
            'username': winner.username,
            'winnings': str(winnings)
        }]

        db.session.add(self)
        db.session.commit()

        # broadcast game-over
        socketio.emit('game-over', {'id': self.id, 'data': self.data }, namespace='/socket.io/')

           
