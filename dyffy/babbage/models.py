#!/usr/bin/env python
"""
Babbage database setup using SQLAlchemy
@author jack@tinybike.net
"""
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, Numeric, DateTime, Boolean, Table, Text, Float
from sqlalchemy import create_engine, func, event, DDL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.schema import MetaData
import pgsql
import config

Base = declarative_base()
engine = create_engine(config.POSTGRES["urlstring"],
                       isolation_level="SERIALIZABLE",
                       echo=False)

EightDecimalPoints = Numeric(precision=23, scale=8, asdecimal=True)

##########################
# Mirror tables in dyffm #
##########################

class User(Base):
    """"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(100))
    password = Column(String(50))
    active = Column(Boolean)
    address = Column(String(100))
    city = Column(String(50))
    state = Column(String(50))
    zipcode = Column(String(20))
    avatar = Column(String(100))

    created = Column(DateTime, default=datetime.datetime.now)
    last_login = Column(DateTime, default=datetime.datetime.now)

    wallet = relationship('Wallet', backref='users', uselist=False)
    transactions = relationship('Transaction', backref='users')


class Wallet(Base):
    """"""
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    dyf_address = Column(String(50))
    dyf_balance = Column(EightDecimalPoints)
    btc_address = Column(String(50))
    btc_balance = Column(EightDecimalPoints)


class Transaction(Base):
    """"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    txhash = Column(String(100))
    txdate = Column(DateTime, default=func.transaction_timestamp())
    amount = Column(EightDecimalPoints)
    currency = Column(String(10), nullable=False)
    coin_address = Column(String(100))
    inbound = Column(Boolean) # True for inbound bridge, False for outbound, NULL for non-bridge
    confirmations = Column(Integer, default=0)
    last_confirmation = Column(DateTime)


class Team(Base):
    """"""
    __tablename__ = "team"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))


###########
# Betting #
###########

class BetHistory(Base):
    """"""
    __tablename__ = "bet_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    red = Column(String(100), nullable=False)
    blue = Column(String(100), nullable=False)
    amount = Column(EightDecimalPoints, nullable=False)
    currency = Column(String(10), nullable=False)
    target = Column(String(10), nullable=False)
    time_of_bet = Column(DateTime, nullable=False,
                         default=func.transaction_timestamp())

    #----------------------------------------------------------------------
    def __init__(self, user_id, red, blue, amount, currency, target):
        """"""
        self.user_id = user_id
        self.red = red
        self.blue = blue
        self.amount = amount
        self.currency = currency
        self.target = target


class Bet(Base):
    """"""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    red = Column(String(100), nullable=False)
    blue = Column(String(100), nullable=False)
    amount = Column(EightDecimalPoints, nullable=False)
    currency = Column(String(10), nullable=False)
    target = Column(String(10), nullable=False)
    time_of_bet = Column(DateTime, nullable=False,
                         default=func.transaction_timestamp())

    #----------------------------------------------------------------------
    def __init__(self, user_id, red, blue, amount, currency, target):
        """"""
        self.user_id = user_id
        self.red = red
        self.blue = blue
        self.amount = amount
        self.currency = currency
        self.target = target

##############
# SoundCloud #
##############

class SoundCloud(Base):
    """"""
    __tablename__ = "soundcloud"

    id = Column(Integer, primary_key=True)
    soundcloud_id = Column(String(100), nullable=False)
    genre = Column(String(25))
    artist = Column(String(100))
    duration = Column(Float, nullable=False)
    favorites = Column(Integer, nullable=False)
    playbacks = Column(Integer, nullable=False)
    mojo = Column(Float, nullable=False)
    updated = Column(DateTime, default=func.transaction_timestamp())


class SoundCloudBattle(Base):
    """"""
    __tablename__ = "soundcloudbattles"

    id = Column(Integer, primary_key=True)
    redtrack = Column(String(100))
    bluetrack = Column(String(100))
    redgenre = Column(String(25))
    bluegenre = Column(String(25))
    duration = Column(Float, nullable=False)
    winner = Column(String(10))
    created = Column(DateTime, default=func.transaction_timestamp())
    started = Column(DateTime)
    finished = Column(DateTime)


###################
# Event listeners #
###################

# When a new user is created, generate a Dyf wallet for them as well
event.listen(User.__table__, "after_create", pgsql.create_wallet)
event.listen(User.__table__, "after_create", pgsql.insert_user_trigger)

# When a bet is placed, create a copy of it in the bet_history table
event.listen(Bet.__table__, "after_create", pgsql.bet_history_record)
event.listen(Bet.__table__, "after_create", pgsql.bet_trigger)

if __name__ == "__main__":

    # Clear all tables
    meta = MetaData()
    meta.reflect(bind=engine)
    for table in reversed(meta.sorted_tables):
        engine.execute(table.delete())

    # Create database session
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # Create some users
    new_users = [
        User(username="Jack", email="jack@dyffy.com"),
        User(username="Scott", email="scott@dyffy.com"),
        User(username="Matt", email="matt@dyffy.com"),
        User(username="testuser", email="test@test.com"),
    ]
    session.add_all(new_users)
    session.commit()

    session.close()
