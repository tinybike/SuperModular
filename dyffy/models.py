import datetime

from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import UserMixin

from decimal import Decimal, ROUND_HALF_EVEN

from dyffy import app

db = SQLAlchemy(app)

EightDecimalPoints = db.Numeric(precision=23, scale=8, asdecimal=True)

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

        friends = {'pending': [], 'accept':[], 'friends':[]}
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

            friends[state].append({'username': f.username, 'id': f.id, 'avatar': f.avatar})

        # get others
        others = []
        for o in User.query.filter(~User.id.in_(ids)).order_by(User.last_login).limit(others_limit).all():

            others.append({'username': o.username, 'id': o.id, 'avatar': o.avatar})

        return friends, others


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
    created = db.Column(db.DateTime, default=datetime.datetime.now)
    started = db.Column(db.DateTime)
    finished = db.Column(db.DateTime)
    min_players = db.Column(db.Integer)
    game_minutes = db.Column(db.Integer)

    bets = db.relationship('Bet', backref='game')
    soundcloud_id = db.Column(db.String(100))

    def add_player(self, user):

        self.players.append(user)

        db.session.commit()


    def add_bet(self, user_id, guess, bet=10):

        user = User.query.get(user_id)
        user.wallet.debit(bet)

        bet = Bet(user_id=user_id, game_id=self.id, amount=bet, guess=guess)

        db.session.add(bet)
        db.session.commit()


    def has_bet(self, user_id):

        if Bet.query.filter_by(game_id=self.id, user_id=user_id).first():
            return True
        else:
            return False

    def start(self):

        self.started = datetime.datetime.now()
        db.session.commit()




