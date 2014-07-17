#!/usr/bin/env python
"""
babbage: state machine callbacks
@author jack@tinybike.net
"""
import datetime
from decimal import *
from fysom import Fysom
import currency
import settle
import account
import data
from utils import *
from models import Bet, Wallet, SoundCloudBattle
import db
import config

def enter_game(e):
    """Enter a game"""
    if config.DEBUG:
        print e.user_id, "enters", e.title
    if e.title == "soundcloud":
        print "Welcome to the SoundCloud game!"
        
def play_game(e):
    """Specify options and start the game"""
    if config.DEBUG:
        print e.user_id, "is now playing", e.title, "(genre:", e.genre + ")"
    data.update(e)
    if e.title == "soundcloud":
        res = (db.session.query(SoundCloudBattle)
                 .filter(SoundCloudBattle.redgenre==e.genre,
                         SoundCloudBattle.bluegenre==e.genre,
                         SoundCloudBattle.started==None,
                         SoundCloudBattle.finished==None)
                 .limit(1)
                 .all())
        if res:
            res[0].started = datetime.datetime.now()
            db.session.commit()
            if config.DEBUG:
                print "Playing:", res[0].redtrack, "vs", res[0].bluetrack, "-", res[0].duration/1000.0, "seconds to go"

def bet(e):
    """Record a bet in the bets table in the database"""
    if config.DEBUG:
        print e.user_id, "bets", e.amount, e.currency ,"on", e.target
    if type(e.amount) != Decimal:
        precision = currency.get_precision(e.currency)
        amount = Decimal(e.amount).quantize(precision,
                                            rounding=ROUND_HALF_EVEN)
    else:
        amount = e.amount
    if account.debit(e.user_id, amount, e.currency,
                     session=db.session, handle_commit=False):
        res = db.session.query(Bet).filter(Bet.user_id==e.user_id,
                                           Bet.red==e.red,
                                           Bet.blue==e.blue,
                                           Bet.target==e.target,
                                           Bet.currency==e.currency).all()
        if res:
            res[0].amount += amount
        else:
            db.session.add(Bet(user_id=e.user_id,
                               red=e.red,
                               blue=e.blue,
                               amount=amount,
                               currency=e.currency,
                               target=e.target))
        db.session.commit()
        print {
            "success": True,
            "red": e.red,
            "blue": e.blue,
            "amount": amount,
            "currency": e.currency,
            "target": e.target,
        }
    else:
        db.session.rollback()
        print {"success": False}

def settle_bets(e):
    """
    It's game over, man.  Game over!
    - If the result is neutral (~zero), return all bets
    - If either side has no betters, return all bets
    - Otherwise, decide winners/losers and determine payouts
    """
    # res.db.session.query(SoundCloudBattle)
    # outcome = settle.event_outcome()

    # if settle.neutral(price_change) or not settle.bets_exist(coin_data['coin_code']):
    #     settle.return_bets(coin_code=coin_data['coin_code'])
    
    # else:
    #     winning_direction = '+' if price_change > 0 else '-'
    #     roster = settle.winners_losers(winning_direction, coin_data['coin_code'])
    #     pools = settle.collect_pools(roster)
    #     winnings, losses = settle.pool_disburse(roster, pools)
    #     settle.store_round_results(winners, losers, winnings, losses)
    
    # settle.prepare_next_round(coin_data['price'], coin_data['coin_code'])
    # settle.reset_bet_tables()

def echo_timestamp(e):
    timestamp = datetime.datetime.now()
    print "@%s: [%s] --%s--> [%s]" % (timestamp, e.src, e.event, e.dst)
