import os, sys, traceback, threading, json, datetime
from functools import wraps
from contextlib import contextmanager
from decimal import *

from flask import request

from dyffy import db
from dyffy import app
from dyffy.coinreactor import CoinReactor

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def prp(o):
    print json.dumps(o, indent=3, sort_keys=True, cls=DecimalEncoder)

####################
# Balance checking #
####################

def user_dyffs_balance(username):
    balance = None
    dyffs_query = "SELECT balance FROM dyffs WHERE username = %s"
    with db.cursor_context() as cur:
        cur.execute(dyffs_query, (username,))
        if cur.rowcount:
            balance = cur.fetchone()[0]
    return balance

def all_users_dyffs_balance():
    balance = {}
    dyffs_query = "SELECT username, balance FROM dyffs"
    with db.cursor_context(True) as cur:
        cur.execute(dyffs_query)
        for row in cur:
            balance[row['username']] = row['balance']
    return balance

####################
# Currency/payment #
####################

def currency_precision(currency_code):
    if currency_code == 'NXT':
        precision = '.01'
    elif currency_code == 'XRP':
        precision = '.000001'
    else:
        precision = '.00000001'
    return precision

def currency_codes(currency, convert_from="symbol", convert_to="name"):
    """Convert between currencies and their three-letter codes"""
    if convert_from == "name" and convert_to == "name":
        convert_to = "symbol"
    query = "SELECT {convert_to} FROM currencies WHERE {convert_from} = %s".format(
        convert_to=convert_to, convert_from=convert_from
    )
    with db.cursor_context() as cur:
        cur.execute(query, (currency,))
        for row in cur:
            return row[0]
    return None

def debit(username, amount, currency):
    balance = False
    debit_complete = False
    balance_query = "SELECT balance FROM dyffs WHERE username = %s"
    with db.cursor_context() as cur:
        cur.execute(balance_query, (username,))
        balance = cur.fetchone()[0]
    if balance and amount <= balance:
        new_balance = balance - amount
        if currency == 'DYF':
            debit_query = (
                "UPDATE dyffs SET balance = balance - %s "
                "WHERE username = %s "
                "RETURNING balance"
            )
            with db.cursor_context() as cur:
                cur.execute(debit_query, (amount, username))
                for row in cur:
                    balance = row[0]
                    debit_complete = balance == new_balance
    if debit_complete:
        return balance
    return False

#################################
# Social network/award tracking #
#################################

def verify_award_tracking_setup():
    select_user_id_query = (
        "SELECT user_id FROM users "
        "WHERE user_id NOT IN "
        "(SELECT DISTINCT user_id FROM award_tracking)"
    )
    insert_award_tracking_query = (
        "INSERT INTO award_tracking (category, user_id) VALUES (%s, %s)"
    )
    with db.cursor_context() as cur:
        cur.execute(select_user_id_query)
        user_ids = [row[0] for row in cur.fetchall()]
        if user_ids:
            cur.execute("SELECT DISTINCT category FROM awards")
            categories = [row[0] for row in cur.fetchall()]
    if user_ids:
        with db.cursor_context() as cur:
            for user_id in user_ids:
                for category in categories:
                    cur.execute(insert_award_tracking_query, (category,
                                                              user_id))

def update_awards(category, user_ids=[]):
    won_awards = None
    number_completed = 0
    number_of_winners = None
    if not user_ids:
        if session and 'user_id' in session:
            user_ids.append(session['user_id'])
    update_tracking_query = (
        "UPDATE award_tracking "
        "SET number_completed = number_completed + 1, "
        "last_completion = now() "
        "WHERE user_id = %s AND category = %s "
        "RETURNING number_completed"
    )
    next_award_query = (
        "SELECT requirement, award_id, award_name FROM awards "
        "WHERE category = %s AND requirement >= %s "
        "ORDER BY requirement LIMIT 1"
    )
    next_award, next_award_id, next_award_name = None, None, None
    with db.cursor_context() as cur:
        for user_id in user_ids:
            cur.execute(update_tracking_query, (user_id, category))
            number_completed = cur.fetchone()[0]
            cur.execute(next_award_query, (category, number_completed))
            if cur.rowcount:
                results = cur.fetchone()
                next_award = {
                    'requirement': int(results[0]),
                    'award_id': results[1],
                    'award_name': results[2],
                }
                if next_award['requirement'] == number_completed:
                    insert_award_winner_query = (
                        "INSERT INTO award_winners "
                        "(award_id, award_name, category, "
                        "user_id, won_on) "
                        "VALUES "
                        "(%(award_id)s, %(award_name)s, %(category)s, "
                        "%(user_id)s, now()) "
                        "RETURNING award_name"
                    )
                    insert_award_winner_parameters = {
                        'award_id': next_award['award_id'],
                        'award_name': next_award['award_name'],
                        'category': category,
                        'user_id': user_id,
                    }
                    cur.execute(insert_award_winner_query,
                                insert_award_winner_parameters)
                    won_awards = cur.fetchone()[0]
                    update_number_of_winners_query = (
                        "UPDATE awards "
                        "SET number_of_winners = number_of_winners + 1 "
                        "WHERE award_id = %s "
                        "RETURNING number_of_winners"
                    )
                    cur.execute(update_number_of_winners_query,
                                (next_award['award_id'],))
                    number_of_winners = cur.fetchone()[0]
    return {
        'won_awards': won_awards,
        'number_completed': number_completed,
        'number_of_winners': number_of_winners,
    }

#########################
# Betting market timing #
#########################

def check_interval(startup=False):
    """60 minute interval checks, for betting markets"""
    now = datetime.datetime.now()
    seconds_remaining = 60 - now.second
    next = 0 if seconds_remaining == 60 else 1
    minutes_remaining = 60 - now.minute - next
    if startup:
        return minutes_remaining*60 + seconds_remaining
    seconds_remaining = str(seconds_remaining)
    if len(seconds_remaining) < 2:
        seconds_remaining = "0" + seconds_remaining
    minutes_remaining = str(minutes_remaining)
    if len(minutes_remaining) < 2:
        minutes_remaining = "0" + minutes_remaining
    return minutes_remaining + ":" + seconds_remaining

def timing_loop(callback):
    """Timer thread for the betting market countdown"""
    def wrapper():
        timing_loop(callback)
        callback()
    delay = check_interval(True)
    timer = threading.Timer(delay, wrapper)
    timer.start()
    return timer

#################################
# Betting markets round closing #
#################################

def final_coin_prices():
    """Coin prices at round closing"""
    select_coins_result = None
    select_coins_query = (
        "SELECT ap.coin, ap.coin_code, ap.price, ap.data_source, "
        "acr.start_price, ap.price/acr.start_price AS ratio "
        "FROM altcoin_prices ap "
        "INNER JOIN altcoin_current_round acr "
        "ON ap.coin_code = acr.coin_code "
        "WHERE acr.start_price > 0 "
        "AND ap.price > 0"
    )
    with db.cursor_context(True) as cur:
        cur.execute(select_coins_query)
        select_coins_result = cur.fetchall()
    for coin_data in select_coins_result:
        yield coin_data

def neutral(price_change):
    """Check whether change is approximately zero"""
    is_zero = price_change < app.config['NEUTRAL_THRESHOLD']
    return is_zero
    
def return_bets(coin_code=None, battle_coin=None):
    """Return all bets to users who made them"""
    bets_returned = 0
    return_bets_query = (
        "UPDATE dyffs "
        "SET balance = balance + subquery.amount "
        "FROM "
        "(SELECT username, amount FROM dyffs "
        "INNER JOIN "
        "altcoin_bets ab "
        "ON ab.better = dyffs.username "
        "WHERE ab.coin_code = %s) "
        "AS subquery "
        "WHERE dyffs.username = subquery.username"
    )
    return_vs_bets_query = (
        "UPDATE dyffs "
        "SET balance = balance + subquery.amount "
        "FROM "
        "(SELECT username, amount FROM dyffs "
        "INNER JOIN "
        "altcoin_vs_bets ab "
        "ON ab.better = dyffs.username "
        "WHERE "
        "ab.left_coin_code = %(left)s AND ab.right_coin_code = %(right)s) "
        "AS subquery "
        "WHERE dyffs.username = subquery.username"
    )
    with db.cursor_context() as cur:
        if coin_code is not None:
            cur.execute(return_bets_query, (coin_code,))
            bets_returned += cur.rowcount
        if battle_coin is not None:
            cur.execute(return_vs_bets_query, battle_coin)
            bets_returned += cur.rowcount
    return bets_returned

def winners_losers(winning_bet, market, market_type='predict'):
    """Determine winning and losing betters"""
    # Predict market
    #   winning_bet: + or -
    #   market: symbol of the coin being bet on (e.g. BTC)
    if market_type == 'predict':
        query = (
            "SELECT better, amount, denomination FROM altcoin_bets "
            "WHERE bet_direction %s %%(bet_direction)s "
            "AND coin_code = %%(coin_code)s"
        )
        parameters = {'bet_direction': winning_bet, 'coin_code': market}
    # Battle market
    #   winning_bet: left or right
    #   market: dict containing the left and right coin codes
    else:
        query = (
            "SELECT better, amount, denomination FROM altcoin_vs_bets "
            "WHERE bet_target %s %%(bet_target)s "
            "AND left_coin_code = %%(left_coin_code)s "
            "AND right_coin_code = %%(right_coin_code)s"
        )
        parameters = {
            'bet_target': market[winning_bet],
            'left_coin_code': market['left'],
            'right_coin_code': market['right'],
        }
    roster = {'win': [], 'loss': []}
    with db.cursor_context() as cur:
        for k, v in {'win': '=', 'loss': '<>'}.items():
            cur.execute(query % v, parameters)
            roster[k] = cur.fetchall()
    return roster

def collect_pools(roster):
    """Winning and losing bet pool sizes"""
    pools = {'win': Decimal(0), 'loss': Decimal(0)}
    for result, users in roster.items():
        for u in users:
            pools[result] += u[1]
    return pools

def pool_disburse(roster, pools):
    """Calculate winnings/losses, disburse pool funds"""
    winnings = {}
    for winner in roster['win']:
        relative_bet_size = winner[1] / pools['win']
        winnings[winner[0]] = winner[1] + relative_bet_size * pools['loss']
    losses = {}
    for loser in roster['loss']:
        relative_bet_size = loser[1] / pools['loss']
        losses[loser[0]] = relative_bet_size * pools['loss']
    return winnings, losses

def store_round_results(winners, losers, winnings, losses):
    """Insert winners/losers into altcoin_results table"""
    insert_results_query = (
        "INSERT INTO altcoin_results "
        "(better, amount_bet, denomination, "
        "amount_won, amount_lost) "
        "VALUES "
        "(%(better)s, %(amount_bet)s, %(denomination)s, "
        "%(amount_won)s, %(amount_lost)s)"
    )
    update_dyffs_win_query = (
        "UPDATE dyffs "
        "SET balance = balance + %s "
        "WHERE username = %s "
        "RETURNING balance"
    )
    update_dyffs_loss_query = (
        "UPDATE dyffs "
        "SET balance = balance - %s "
        "WHERE username = %s "
        "RETURNING balance"
    )
    with db.cursor_context() as cur:
        for winner in winners:
            insert_results_parameters = {
                'better': winner[0],
                'amount_bet': winner[1],
                'denomination': winner[2],
                'amount_won': winnings[winner[0]],
                'amount_lost': None,
            }
            cur.execute(insert_results_query, insert_results_parameters)
            cur.execute(update_dyffs_win_query, (winnings[winner[0]],
                                                 winner[0]))
        for loser in losers:
            insert_results_parameters = {
                'better': loser[0],
                'amount_bet': loser[1],
                'denomination': loser[2],
                'amount_won': None,
                'amount_lost': losses[loser[0]],
            }
            cur.execute(insert_results_query, insert_results_parameters)
            cur.execute(update_dyffs_loss_query, (losses[loser[0]],
                                                  loser[0]))

def reset_bet_tables():
    """Clear betting tables for the next round"""
    bets_reset = 0
    with db.cursor_context() as cur:
        for table in app.config['BET_TABLES']:
            cur.execute("DELETE FROM %s" % table)
            bets_reset += cur.rowcount
    return bets_reset

def prepare_next_round(price, coin_code):
    """Get updated price for the next round"""
    start_price_query = (
        "UPDATE altcoin_current_round "
        "SET start_price = %(start_price)s, "
        "price_change = NULL, end_price = NULL "
        "WHERE coin_code = %(coin_code)s"
    )
    start_price_parameters = {'start_price': price, 'coin_code': coin_code}
    with db.cursor_context() as cur:
        cur.execute(start_price_query, start_price_parameters)

def bet_counts(market, market_type='predict'):
    """Count the number of bets on both sides of the market"""
    bet_count = {}
    # Predict market
    #   possible bets: + or -
    #   market: symbol of the coin being bet on (e.g. BTC)
    if market_type == 'predict':
        query = (
            "SELECT count(*) FROM altcoin_bets "
            "WHERE coin_code = %(coin_code)s "
            "AND bet_direction = %(bet_direction)s"
        )
        with db.cursor_context() as cur:
            for bet in ('+', '-'):
                parameters = {'coin_code': market, 'bet_direction': bet}
                cur.execute(query, parameters)
                bet_count[bet] = cur.fetchone()[0]
    # Battle market
    #   possible bets: left or right
    #   market: dict containing the left and right coin codes
    else:
        query = (
            "SELECT count(*) FROM altcoin_vs_bets "
            "WHERE left_coin_code = %(left_coin_code)s "
            "AND right_coin_code = %(right_coin_code)s "
            "AND bet_target = %(bet_target)s"
        )
        with db.cursor_context() as cur:
            for bet in ('left', 'right'):
                parameters = {
                    'left_coin_code': market['left'],
                    'right_coin_code': market['right'],
                    'bet_target': market[bet],
                }
                cur.execute(query, parameters)
                bet_count[bet] = cur.fetchone()[0]
    return bet_count

def bets_exist(market, market_type='predict'):
    """Make sure both sides of the market are populated"""
    # Predict market
    #   possible bets: + or -
    #   market: symbol of the coin being bet on (e.g. BTC)
    if market_type == 'predict':
        query = (
            "SELECT EXISTS("
            "(SELECT 1 FROM altcoin_bets "
            "WHERE coin_code = %(coin_code)s "
            "AND bet_direction = '+') "
            "INTERSECT "
            "(SELECT 1 FROM altcoin_bets "
            "WHERE coin_code = %(coin_code)s "
            "AND bet_direction = '-'))"
        )
        parameters = {'coin_code': market}
    # Battle market
    #   possible bets: left or right
    #   market: dict containing the left and right coin codes
    else:
        query = (
            "SELECT EXISTS("
            "(SELECT 1 FROM altcoin_vs_bets "
            "WHERE left_coin_code = %(left_coin_code)s "
            "AND right_coin_code = %(right_coin_code)s "
            "AND bet_target = %(left_coin_code)s) "
            "INTERSECT "
            "(SELECT 1 FROM altcoin_vs_bets "
            "WHERE left_coin_code = %(left_coin_code)s "
            "AND right_coin_code = %(right_coin_code)s "
            "AND bet_target = %(right_coin_code)s))"
        )
        parameters = {
            'left_coin_code': market['left'],
            'right_coin_code': market['right'],
        }
    with db.cursor_context() as cur:
        cur.execute(query, parameters)
        return cur.fetchone()[0]

def round_complete():
    """End of betting round"""
    if not app.config['TESTING']:
        # Get most recent coin data
        from dyffy.pricer import Pricer
        Pricer().update_data()
    for coin_data in final_coin_prices():
        # Determine the price change, and disburse the bet pools
        # - If the result is neutral (~zero), return all bets
        # - If either side has no betters, return all bets
        # - Otherwise, decide winners/losers and determine payouts
        price_change = coin_data['price'] - coin_data['start_price']
        if neutral(price_change) or not bets_exist(coin_data['coin_code']):
            return_bets(coin_code=coin_data['coin_code'])
        else:
            winning_direction = '+' if price_change > 0 else '-'
            roster = winners_losers(winning_direction, coin_data['coin_code'])
            pools = collect_pools(roster)
            winnings, losses = pool_disburse(roster, pools)
            store_round_results(winners, losers, winnings, losses)
        prepare_next_round(coin_data['price'], coin_data['coin_code'])
    reset_bet_tables()
