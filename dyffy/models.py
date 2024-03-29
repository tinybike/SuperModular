import datetime, json

from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.types import TypeDecorator, VARCHAR

from flask.ext.login import UserMixin

from decimal import Decimal, ROUND_HALF_EVEN
import threading

import pandas as pd
import soundcloud
import time

from dyffy import app

db = SQLAlchemy(app)

# pandas display options
pd.set_option("display.max_rows", 25)
pd.set_option("display.width", 1000)
pd.options.display.mpl_style = "default"

EightDecimalPoints = db.Numeric(precision=23, scale=8, asdecimal=True)


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

    Usage::

        JSONEncodedDict(255)

    """

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


# many-to-many tables
teams = db.Table('teams',
    db.Column('team_id', db.Integer, db.ForeignKey('team.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)
players = db.Table('players',
    db.Column('game_id', db.Integer, db.ForeignKey('game.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
) 

class Friend(db.Model):

    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    status = db.Column(db.Boolean, default=False)

    def accept(self):

        self.status = True
        db.session.commit()

    def reject(self):

        db.session.delete(self)
        db.session.commit()


class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    active = db.Column(db.Boolean)
    name = db.Column(db.String(50))
    address = db.Column(db.String(100))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zipcode = db.Column(db.String(20))
    avatar = db.Column(db.String(100))

    facebook_id = db.Column(db.BigInteger)
    facebook_access_token = db.Column(db.String(255))

    created = db.Column(db.DateTime, default=datetime.datetime.now)
    last_login = db.Column(db.DateTime, default=datetime.datetime.now)

    wallet = db.relationship('Wallet', backref='user', uselist=False)
    bets = db.relationship('Bet', backref='user', uselist=False)

    transactions = db.relationship('Transaction', backref='user')
    
    teams = db.relationship('Team', secondary=teams, backref=db.backref('users', lazy='dynamic'))
    games = db.relationship('Game', secondary=players, backref=db.backref('players', lazy='dynamic'))

    @classmethod
    def create_user(cls, password=None, facebook_id=None, **kwargs):

        if password:

            user = cls(password=generate_password_hash(password), **kwargs)
            db.session.add(user)
            db.session.commit()

            user.create_wallet()

            return user

        elif facebook_id:

            user = cls(facebook_id=facebook_id, **kwargs)
            if not kwargs.get('username') and kwargs.get('name'):
                user.username = kwargs['name'].split(' ')[0]

            db.session.add(user)
            db.session.commit()

            user.create_wallet()

            return user


    @classmethod
    def get_user(cls, password=None, facebook_id=None, **kwargs):

        if password and kwargs.get('username'):

            user = cls.query.filter_by(username=kwargs['username']).first()

            if check_password_hash(user.password, password):
            
                return user

        elif facebook_id:

            user = cls.query.filter_by(facebook_id=facebook_id).first()

            if user:
                return user



    def request_friend(self, friend_id):

        if User.query.get(friend_id):

            friend = Friend(user1_id=self.id, user2_id=friend_id)

            db.session.add(friend)
            db.session.commit()

            return True

        else:

            return False


    def get_friends(self, others_limit=50):

        friends = []
        ids = [self.id]  # hack for others query

        for u in Friend.query.filter((Friend.user1_id == self.id) | (Friend.user2_id == self.id)).all():

            if u.user1_id == self.id:
                f = User.query.get(u.user2_id)
                state = 'pending' if not u.status else 'friends'
                ids.append(u.user2_id)
            else:
                f = User.query.get(u.user1_id)
                state = 'accept' if not u.status else 'friends'
                ids.append(u.user1_id)

            friends.append({'username': f.username, 'id': f.id, 'avatar': f.avatar, 'status': state})

        # get others
        others = []
        for o in User.query.filter(~User.id.in_(ids)).order_by(User.last_login).limit(others_limit).all():

            others.append({'username': o.username, 'id': o.id, 'avatar': o.avatar})

        return friends, others

    def get_open_games(self):

        open_games = Game.query.filter(Game.players.any(id=self.id), Game.finished != None)

        return open_games


    def create_wallet(self, initial_dyf=100):

        new_wallet = Wallet(user_id=self.id)
        new_wallet.dyf_balance = initial_dyf

        db.session.add(new_wallet)
        db.session.commit()


class Wallet(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    dyf_balance = db.Column(EightDecimalPoints)
    btc_address = db.Column(db.String(50))
    btc_balance = db.Column(EightDecimalPoints)

    def debit(self, amount, currency="DYF", handle_commit=False):
        """
        Debit coins from a wallet.  handle_commit should be False if your
        transaction includes a debit in combination with other actions.
        """
        debit_complete = False
        if currency == "NXT":
            precision = ".01"
        elif currency == "XRP":
            precision = ".000001"
        else:
            precision = ".00000001"
        amount = Decimal(amount).quantize(Decimal(precision),
                                          rounding=ROUND_HALF_EVEN)
        if currency == "DYF":
            balance = self.dyf_balance
        elif currency == "BTC":
            balance = self.btc_balance
        if balance and amount <= balance:
            new_balance = balance - amount
            if currency == "DYF":
                self.dyf_balance -= amount
            elif currency == "BTC":
                self.btc_balance -= amount
            debit_complete = True
            if handle_commit:
                db.session.commit()
        if debit_complete:
            return new_balance
        if handle_commit:
            db.session.rollback()
        return False


class Transaction(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(EightDecimalPoints)
    currency = db.Column(db.Float)
    date = db.Column(db.DateTime)


class Team(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))


class Chat(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50))   # user.username
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)


class Bet(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    amount = db.Column(EightDecimalPoints, nullable=False)
    guess = db.Column(db.String(100), nullable=False)
    time_of_bet = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)


class Game(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    created = db.Column(db.DateTime, default=datetime.datetime.now)

    starts_at = db.Column(db.DateTime)
    started = db.Column(db.Boolean)
    ends_at = db.Column(db.DateTime)
    finished = db.Column(db.Boolean)

    rules = db.Column(MutableDict.as_mutable(JSONEncodedDict(255)), default={})
    data = db.Column(MutableDict.as_mutable(JSONEncodedDict(255)), default={})

    no_more_bets = db.Column(db.Boolean, default=False)

    bets = db.relationship('Bet', backref='game')

    def add_player(self, user):

        if not user in self.players:

            self.players.append(user)

    def add_bet(self, user_id, guess, amount):

        user = User.query.get(user_id)
        user.wallet.debit(amount)

        bet = Bet(user_id=user_id, game_id=self.id, amount=amount, guess=guess)

        db.session.add(bet)
        db.session.commit()

    def has_bet(self, user_id):

        if Bet.query.filter_by(game_id=self.id, user_id=user_id).first():
            return True
        else:
            return False

    def start(self, on_finish=None):

        if not self.started:

            self.starts_at = datetime.datetime.now()
            self.started = True
            
            duration = None

            # set timer for absolute end time
            if self.ends_at:

                duration = (self.ends_at - self.starts_at).seconds

            # set timer for relative end time
            elif self.rules.get('duration'):

                self.ends_at = self.starts_at + datetime.timedelta(minutes = self.rules['duration'])
                duration = self.rules['duration'] * 60

            if duration:

                if not on_finish:
                    on_finish = self.finish

                # start request independent timer with callback
                threading.Timer(duration, on_finish).start()


    def finish(self):

        self.finished = True


class SoundCloud(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    soundcloud_id = db.Column(db.Integer)
    genre = db.Column(db.String(250))
    artist = db.Column(db.String(250))
    duration = db.Column(db.Float)
    favorites = db.Column(db.Integer)
    playbacks = db.Column(db.Integer)
    mojo = db.Column(db.Float)
    played = db.Column(db.Boolean)
    updated = db.Column(db.DateTime, default=db.func.transaction_timestamp())

    current_time = datetime.datetime.now()

    @classmethod
    def update(self):
        """Download data from the SoundCloud API"""
        # Check if we have a recent song list (< 10 mins old)
        res = (db.session.query(SoundCloud)
                 .order_by(SoundCloud.updated.desc())
                 .limit(1)
                 .all())
        if res:
            time_elapsed = datetime.datetime.now() - res[0].updated
            total_minutes = float(time_elapsed.total_seconds()) / 60.0
            if total_minutes < 10:
                app.logger.info("SoundCloud data up-to-date: %d minutes since last update" % total_minutes)
                return

        self.query.delete()
        db.session.commit()

        for genre in ("rock", ):#, "punk", "dubstep", "techno", "rap"):

            try:
                # Create the SoundCloud API client
                client = soundcloud.Client(client_id=app.config["SOUNDCLOUD_ID"],
                                       client_secret=app.config["SOUNDCLOUD_SECRET"],
                                       username=app.config["SOUNDCLOUD_USERNAME"],
                                       password=app.config["SOUNDCLOUD_PASSWORD"])

                # Get audio track list for selected genre from the SoundCloud API
                tracks = client.get("/tracks",
                                    genres=genre,
                                    types="recording,live,remix,original",
                                    sharing="public",
                                    limit=100)
            except Exception, e:
                app.logger.error(e)
                continue

            # Extract the data into a dataframe
            track_data = []
            for t in tracks:
                try:
                    if t.embeddable_by != "all" or not t.streamable:
                        continue
                    row = [t.id, str(t.genre), t.user_id, t.duration,
                           t.favoritings_count, t.playback_count]  
                except Exception, e: 
                    app.logger.error(e)
                    continue

                track_data.append(row)
            df = pd.DataFrame(track_data,
                              columns=["soundcloud_id", "genre", "artist",
                                       "duration", "favorites", "playbacks"])
            
            # Calculate song's "mojo" (%) as a sum of normalized
            # favorites and playbacks
            df["updated"] = datetime.datetime.now()
            df["mojo"] = 50*(df.favorites/float(max(df.favorites)) +
                             df.playbacks/float(max(df.playbacks)))
            df = df.sort("mojo", ascending=False)

            # Insert the ranked tracks into the database
            df.to_sql("sound_cloud", db.engine, if_exists="append", index=False)
            
            # Pause so we don't spam the Soundcloud API
            time.sleep(1)
    
    @classmethod
    def get_random_track(self):

        track = self.query.filter(self.played==None).order_by(self.mojo.desc()).first()
        if track is None:
            track = self.query.order_by(self.mojo.desc()).first()
        else:
            track.played = True
        db.session.commit()
        return {
            "id": track.soundcloud_id,
            "playbacks": track.playbacks,
            "favorites": track.favorites,
        }


    @classmethod
    def get_track(self, track_id):

        track = self.query.filter(self.soundcloud_id==track_id).first()

        try:
            client = soundcloud.Client(
                client_id=app.config["SOUNDCLOUD_ID"],
                client_secret=app.config["SOUNDCLOUD_SECRET"],
                username=app.config["SOUNDCLOUD_USERNAME"],
                password=app.config["SOUNDCLOUD_PASSWORD"]
            )
            updated_track = client.get("/tracks", ids=track_id, limit=1)[0]
            track.favorites = updated_track.favoritings_count
            track.playbacks = updated_track.playbacks_count
            db.session.commit()
        except Exception, e:
            app.logger.error(e)

        return {
            "id": track.soundcloud_id,
            "playbacks": track.playbacks,
            "favorites": track.favorites,
        }
