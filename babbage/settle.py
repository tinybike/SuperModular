#################################
# Betting markets round closing #
#################################

from decimal import *
from models import *
import currency
import config

def neutral(price_change):
    """Check whether change is approximately zero"""
    is_zero = price_change < config.NEUTRAL_THRESHOLD
    return is_zero

def event_outcome():
    """Get the final outcome of the event being bet on."""


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
    with cursor_context() as cur:
        if coin_code is not None:
            cur.execute(return_bets_query, (coin_code,))
            bets_returned += cur.rowcount
        if battle_coin is not None:
            cur.execute(return_vs_bets_query, battle_coin)
            bets_returned += cur.rowcount
    return bets_returned

def winners_losers(winning_bet, market, market_type='predict'):
    """Determine winning and losing betters"""
    # Battle market
    #   winning_bet: left or right
    #   market: dict containing the left and right coin codes
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
    with cursor_context() as cur:
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
    with cursor_context() as cur:
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
    with cursor_context() as cur:
        for table in config.BET_TABLES:
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
    with cursor_context() as cur:
        cur.execute(start_price_query, start_price_parameters)

def bet_counts(market, market_type='predict'):
    """Count the number of bets on both sides of the market"""
    bet_count = {}
    # Battle market
    #   possible bets: left or right
    #   market: dict containing the left and right coin codes
    query = (
        "SELECT count(*) FROM altcoin_vs_bets "
        "WHERE left_coin_code = %(left_coin_code)s "
        "AND right_coin_code = %(right_coin_code)s "
        "AND bet_target = %(bet_target)s"
    )
    with cursor_context() as cur:
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
    # Battle market
    #   possible bets: left or right
    #   market: dict containing the left and right coin codes
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
    with cursor_context() as cur:
        cur.execute(query, parameters)
        return cur.fetchone()[0]
