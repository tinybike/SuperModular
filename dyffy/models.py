import datetime

from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import UserMixin, RoleMixin
from flask.ext.security.signals import user_registered	

from dyffy import app

db = SQLAlchemy(app)

EightDecimalPoints = db.Numeric(precision=23, scale=8, asdecimal=True)

# many-to-many tables
roles = db.Table('roles',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)
teams = db.Table('teams',
    db.Column('team_id', db.Integer, db.ForeignKey('team.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

class Friend(db.Model):

    user1_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    status = db.Column(db.Boolean, default=False)

    def accept(self):

    	self.status = True
    	db.session.commit()


class User(db.Model, UserMixin):

	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(50))
	email = db.Column(db.String(100))
	password = db.Column(db.String(50))
	active = db.Column(db.Boolean)
	address = db.Column(db.String(100))
	city = db.Column(db.String(50))
	state = db.Column(db.String(50))
	zipcode = db.Column(db.String(20))
	avatar = db.Column(db.String(100))

	created = db.Column(db.DateTime, default=datetime.datetime.now)
	last_login = db.Column(db.DateTime, default=datetime.datetime.now)

	wallet = db.relationship('Wallet', backref='user', uselist=False)
	transactions = db.relationship('Transaction', backref='user')
	teams = db.relationship('Team', secondary=teams, backref=db.backref('users', lazy='dynamic'))
	roles = db.relationship('Role', secondary=roles, backref=db.backref('users', lazy='dynamic'))

	def request_friend(self, friend_id):

		if User.query.get(friend_id):

			friend = Friend(user_id=self.id, friend_id=friend_id)

			db.session.add(friend)
			db.session.commit()

			return True

		else:

			return False

	def get_friends(self):

		friends = []
		for f in Friend.query.filter((Friend.user1_id == self.id) | (Friend.user2_id == self.id)).all():
			if f.user2_id == self.id:
				friends.append(User.query.get(f.user1_id))
			else:
				friends.append(User.query.get(f.user2_id))

		return friends


	def get_others(self, flat=False, limit=50):

		return User.query.filter(User.id != self.id).order_by(User.last_login).limit(limit).all()


	def create_wallet(self, initial_dyf=100):

		new_wallet = Wallet(user_id=self.id)
		new_wallet.dyf_balance = initial_dyf

		db.session.add(new_wallet)
		db.session.commit()


class Role(db.Model, RoleMixin):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))



class Wallet(db.Model):

	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	dyf_balance = db.Column(EightDecimalPoints)
	btc_address = db.Column(db.String(50))
	btc_balance = db.Column(EightDecimalPoints)


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
    red = db.Column(db.String(100), nullable=False)
    blue = db.Column(db.String(100), nullable=False)
    amount = db.Column(EightDecimalPoints, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    target = db.Column(db.String(10), nullable=False)
    time_of_bet = db.Column(db.DateTime, nullable=False, default=db.func.transaction_timestamp())


class BetHistory(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    red = db.Column(db.String(100), nullable=False)
    blue = db.Column(db.String(100), nullable=False)
    amount = db.Column(EightDecimalPoints, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    target = db.Column(db.String(10), nullable=False)
    time_of_bet = db.Column(db.DateTime, nullable=False, default=db.func.transaction_timestamp())
