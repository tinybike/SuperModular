#!/usr/bin/env python
"""
Dyffy back-end core
(c) Jack Peterson (jack@tinybike.net), 4/19/2014
"""
from __future__ import division

import base64

from flask import session, escape
from flask.ext.login import login_user, logout_user
from flask.ext.socketio import emit

from dyffy.pricer import Pricer
from dyffy.utils import *
from dyffy.guard import Guard
from dyffy.models import User

from dyffy import app
from dyffy import socketio
from dyffy import db

@socketio.on('facebook-profile-data', namespace='/socket.io/')
def facebook_profile_data(req):
    if session and 'user' in session:
        update_users_query = (
            "UPDATE users "
            "SET firstname = %(firstname)s, lastname = %(lastname)s, "
            "gender = %(gender)s, location = %(location)s, "
            "biography = %(biography)s, facebook_url = %(facebook_url)s, "
            "profile_pic = %(profile_pic)s, user_fb_id = %(user_fb_id)s, "
            "user_fb_name = %(user_fb_name)s, fb_connect = 't' "
            "WHERE username = %(username)s AND fb_connect IS NULL"
        )
        gender = 'M' if req['gender'] == 'male' else 'F'
        update_users_parameters = {
            'user_fb_id': req['id'],
            'user_fb_name': req['username'],
            'firstname': req['first_name'],
            'lastname': req['last_name'],
            'gender': gender,
            'location': req['location_name'],
            'biography': req['bio'],
            'facebook_url': req['link'],
            'profile_pic': req['picture'],
            'username': session['user'],
        }
        with db.cursor_context() as cur:
            cur.execute(update_users_query, update_users_parameters)

@socketio.on('record-facebook-friends', namespace='/socket.io/')
def record_facebook_friends(req):
    if session and 'user' in session:
        select_friends_query = (
            "SELECT friend_fb_id FROM facebook_friends WHERE username = %s"
        )
        with db.cursor_context() as cur:
            cur.execute(select_friends_query, (session['user'],))
            existing_friends = [row[0] for row in cur.fetchall()]
        insert_friend_query = (
            "INSERT INTO facebook_friends "
            "(username, "
            "friend_fb_id, friend_fb_name) "
            "VALUES "
            "(%(username)s, "
            "%(friend_fb_id)s, %(friend_fb_name)s)"
        )
        with db.cursor_context() as cur:
            for friend in req['friends']:
                if friend['id'] not in existing_friends:
                    insert_friend_parameters = {
                        'username': session['user'],
                        'friend_fb_id': friend['id'],
                        'friend_fb_name': friend['name'],
                    }
                    cur.execute(insert_friend_query, insert_friend_parameters)

@socketio.on('select-pic', namespace='/socket.io/')
def select_pic(req):
    if session and 'user' in session:
        update_query = (
            "UPDATE facebook_friends "
            "SET rating = rating + %(rating)s, time_of_rating = now() "
            "WHERE username = %(username)s AND friend_fb_id = %(friend_fb_id)s"
        )
        update_target_parameters = {
            'rating': 1,
            'username': session['user'],
            'friend_fb_id': req['target'],
        }
        update_untarget_parameters = {
            'rating': -1,
            'username': session['user'],
            'friend_fb_id': req['untarget'],
        }
        with db.cursor_context() as cur:
            cur.execute(update_query, update_target_parameters)
            cur.execute(update_query, update_untarget_parameters)

@socketio.on('get-current-prices', namespace='/socket.io/')
def get_current_prices(req):
    currency = currency_codes(req['coin'], convert_from='name')
    price_query = (
        "SELECT price, price_change, last_update FROM altcoin_prices "
        "WHERE coin_code = %s"
    )
    price_change_query = (
        "SELECT start_price FROM altcoin_current_round "
        "WHERE coin_code = %s"
    )
    price = None
    price_change = None
    price_ratio = None
    with db.cursor_context() as cur:
        cur.execute(price_query, (currency,))
        for row in cur:
            price = row
        if price is not None:
            cur.execute(price_change_query, (currency,))
            for row in cur:
                price_change = price[0] - row[0]
                if row[0]:
                    price_ratio = price[0] / row[0]
    if price is not None:
        if price_change is not None:
            price_change = float(price_change)
        if price_ratio is not None:
            price_ratio = float(price_ratio)
        current_prices = {
            'price': float(price[0]),
            'price_change': price_change,
            'price_ratio': price_ratio,
            'last_update': int(price[2]),
        }
        if 'battle' in req:
            if req['battle'] == 'left':
                signal = 'current-left-prices'
            else:
                signal = 'current-right-prices'
        else:
            signal = 'current-prices'
        emit(signal, current_prices)

@socketio.on('get-dyff-balance', namespace='/socket.io/')
def get_dyff_balance():
    balance = None
    if 'user' in session:
        dyffs_query = "SELECT balance FROM dyffs WHERE username = %s"
        with db.cursor_context() as cur:
            cur.execute(dyffs_query, (session['user'],))
            for row in cur:
                balance = float(row[0])
    emit('dyff-balance', {'balance': balance})

@socketio.on('get-time-remaining', namespace='/socket.io/')
def get_time_remaining(req=None):
    coin = req['coin'] if req is not None else 'Bitcoin'
    currency = currency_codes(coin, convert_from='name')
    time_remaining = check_interval()
    emit('time-remaining', {'time_remaining': time_remaining})

@socketio.on('predict-bets', namespace='/socket.io/')
def predict_bets(req):
    """Fetch predict market bets"""
    query = (
        "SELECT better, amount, denomination, time_of_bet, bet_direction "
        "FROM altcoin_bets WHERE coin_code = %s ORDER BY time_of_bet DESC"
    )
    currency = currency_codes(req['coin'], convert_from='name')
    starting_price_query = (
        "SELECT start_price FROM altcoin_current_round "
        "WHERE coin_code = %s"
    )
    bets_down = []
    bets_up = []
    starting_price = {}
    with db.cursor_context(True) as cur:
        cur.execute(query, (currency,))
        for row in cur:
            if row['bet_direction'] == '-':
                bets_down.append([row['better'], float(row['amount']),
                                 row['denomination'], str(row['time_of_bet'])])
            else:
                bets_up.append([row['better'], float(row['amount']),
                               row['denomination'], str(row['time_of_bet'])])
        cur.execute(starting_price_query, (currency,))
        for row in cur:
            starting_price = {'price': float(row['start_price'])}
    predict_data = {
        'bets_down': bets_down,
        'bets_up': bets_up,
        'starting_price': starting_price,
    }
    emit('predict-data', predict_data)

@socketio.on('battle-bets', namespace='/socket.io/')
def battle_bets(req):
    """Fetch battle market bets"""
    query = (
        "SELECT better, left_coin_code, right_coin_code, "
        "bet_target, amount, denomination, time_of_bet "
        "FROM altcoin_vs_bets "
        "WHERE bet_target IN (%s, %s) "
        "ORDER BY time_of_bet DESC"
    )
    left_currency = currency_codes(req['left'], convert_from='name')
    right_currency = currency_codes(req['right'], convert_from='name')
    current_price_query = (
        "SELECT start_price FROM altcoin_current_round WHERE coin_code = %s"
    )
    bets_left = []
    bets_right = []
    current_price = {}
    with db.cursor_context(True) as cur:
        cur.execute(query, (left_currency, right_currency))
        for row in cur:
            if row and 'bet_target' in row:
                if row['bet_target'] == left_currency:
                    bets_left.append([row['better'], float(row['amount']),
                                     row['denomination'], str(row['time_of_bet'])])
                else:
                    bets_right.append([row['better'], float(row['amount']),
                                      row['denomination'], str(row['time_of_bet'])])
        cur.execute(current_price_query, (left_currency,))
        for row in cur:
            current_price['left'] = float(row['start_price'])
        cur.execute(current_price_query, (right_currency,))
        for row in cur:
            current_price['right'] = float(row['start_price'])
    emit('battle-data', {
        'bets_left': bets_left,
        'bets_right': bets_right,
        'current_price': current_price,
    })

@socketio.on('predict-bet', namespace='/socket.io/')
def predict_bet(req):
    """Record bet in altcoin_bets table"""
    coin_code = currency_codes(req['market'], 'name')
    precision = currency_precision(req['denomination'])
    if debit(session['user'], req['amount'], req['denomination']):
        select_bets_query = (
            "SELECT better, amount FROM altcoin_bets "
            "WHERE better = %s AND coin_code = %s AND bet_direction = %s"
        )
        existing_bet = None
        with db.cursor_context() as cur:
            cur.execute(select_bets_query, (session['user'],
                                            coin_code,
                                            req['direction']))
            for row in cur:
                existing_bet = row[0]
        if existing_bet is not None:
            insert_bet_query = (
                "UPDATE altcoin_bets SET "
                "amount = amount + %(amount)s, time_of_bet = now() "
                "WHERE "
                "better = %(better)s AND coin_code = %(coin_code)s "
                "AND bet_direction = %(bet_direction)s "
                "RETURNING time_of_bet"
            )
            insert_bet_history_query = (
                "INSERT INTO altcoin_bet_history "
                "(better, coin, coin_code, amount, "
                "denomination, bet_direction, time_of_bet) "
                "VALUES "
                "(%(better)s, %(coin)s, %(coin_code)s, %(amount)s, "
                "%(denomination)s, %(bet_direction)s, now())"
            )
        else:
            insert_bet_query = (
                "INSERT INTO altcoin_bets "
                "(better, coin, coin_code, amount, "
                "denomination, bet_direction, time_of_bet) "
                "VALUES "
                "(%(better)s, %(coin)s, %(coin_code)s, %(amount)s, "
                "%(denomination)s, %(bet_direction)s, now()) "
                "RETURNING time_of_bet"
            )
        amount = Decimal(req['amount']).quantize(Decimal(precision),
                                                 rounding=ROUND_HALF_EVEN)
        insert_bet_parameters = {
            'better': session['user'],
            'coin': req['market'],
            'coin_code': coin_code,
            'amount': amount,
            'denomination': req['denomination'],
            'bet_direction': req['direction'],
        }
        time_of_bet = None
        with db.cursor_context() as cur:
            if existing_bet is not None:
                cur.execute(insert_bet_history_query, insert_bet_parameters)
            cur.execute(insert_bet_query, insert_bet_parameters)
            for row in cur:
                time_of_bet = str(row[0])
        if time_of_bet is not None:
            emit('predict-bet-response', {
                'success': True,
                'time_of_bet': time_of_bet,
                'coin': req['market'],
                'amount': req['amount'],
                'denomination': req['denomination'],
                'bet_direction': req['direction'],
            })
        else:
            emit('predict-bet-response', {'success': False})
    else:
        emit('predict-bet-response', {'success': False})

@socketio.on('battle-bet', namespace='/socket.io/')
def battle_bet(req):
    """Record battle market bet in altcoin_vs_bets table"""
    left_coin_code = currency_codes(req['left'], 'name')
    right_coin_code = currency_codes(req['right'], 'name')
    target_coin_code = currency_codes(req['target'], 'name')
    precision = currency_precision(req['denomination'])
    if debit(session['user'], req['amount'], req['denomination']):
        select_bets_query = (
            "SELECT better, amount FROM altcoin_vs_bets "
            "WHERE better = %s AND left_coin_code = %s "
            "AND right_coin_code = %s AND bet_target = %s"
        )
        existing_bet = None
        with db.cursor_context() as cur:
            cur.execute(select_bets_query, (session['user'],
                                            left_coin_code,
                                            right_coin_code,
                                            target_coin_code))
            for row in cur:
                existing_bet = row[0]
        if existing_bet is not None:
            insert_bet_query = (
                "UPDATE altcoin_vs_bets SET "
                "amount = amount + %(amount)s, time_of_bet = now() "
                "WHERE "
                "better = %(better)s AND left_coin_code = %(left_coin_code)s "
                "AND right_coin_code = %(right_coin_code)s "
                "AND bet_target = %(bet_target)s "
                "RETURNING time_of_bet"
            )
            insert_bet_history_query = (
                "INSERT INTO altcoin_vs_bet_history "
                "(better, left_coin, right_coin, "
                "left_coin_code, right_coin_code, "
                "amount, denomination, "
                "bet_target, time_of_bet) "
                "VALUES "
                "(%(better)s, %(left_coin)s, %(right_coin)s, "
                "%(left_coin_code)s, %(right_coin_code)s, "
                "%(amount)s, %(denomination)s, "
                "%(bet_target)s, now())"
            )
        else:
            insert_bet_query = (
                "INSERT INTO altcoin_vs_bets "
                "(better, left_coin, right_coin, "
                "left_coin_code, right_coin_code, "
                "amount, denomination, "
                "bet_target, time_of_bet) "
                "VALUES "
                "(%(better)s, %(left_coin)s, %(right_coin)s, "
                "%(left_coin_code)s, %(right_coin_code)s, "
                "%(amount)s, %(denomination)s, "
                "%(bet_target)s, now()) "
                "RETURNING time_of_bet"
            )
        amount = Decimal(req['amount']).quantize(Decimal(precision),
                                                 rounding=ROUND_HALF_EVEN)
        insert_bet_parameters = {
            'better': session['user'],
            'left_coin': req['left'],
            'right_coin': req['right'],
            'left_coin_code': left_coin_code,
            'right_coin_code': right_coin_code,
            'amount': amount,
            'denomination': req['denomination'],
            'bet_target': target_coin_code,
        }
        time_of_bet = None
        with db.cursor_context() as cur:
            if existing_bet is not None:
                cur.execute(insert_bet_history_query, insert_bet_parameters)
            cur.execute(insert_bet_query, insert_bet_parameters)
            for row in cur:
                time_of_bet = str(row[0])
        if time_of_bet is not None:
            emit('battle-bet-response', {
                'success': True,
                'time_of_bet': time_of_bet,
                'left_coin': req['left'],
                'right_coin': req['right'],
                'amount': req['amount'],
                'denomination': req['denomination'],
                'bet_target': target_coin_code,
            })
        else:
            emit('battle-bet-response', {'success': False})
    else:
        emit('battle-bet-response', {'success': False})

@socketio.on('admin-end-round', namespace='/socket.io/')
def admin_end_round():
    print "Administrator ended betting round early!"
    round_complete()

@socketio.on('get-awards-list', namespace='/socket.io/')
def awards_list():
    query = (
        "SELECT award_name, category, points, award_description, icon "
        "FROM awards"
    )
    awards = []
    with db.cursor_context(True) as cur:
        cur.execute(query)
        for row in cur:
            awards.append(row)
    emit('awards-list', {'awards': awards})

@socketio.on('friend-request', namespace='/socket.io/')
def friend_request(req):
    '''
    Make a new friend request
    (called by the requester)
    '''
    friend_request_query = (
        "INSERT INTO friend_requests "
        "(requester_id, requester_name, requester_icon, "
        "requestee_id, requestee_name, request_time) "
        "VALUES "
        "(%(requester_id)s, %(requester_name)s, %(requester_icon)s, "
        "%(requestee_id)s, %(requestee_name)s, now()) "
        "RETURNING requestee_name"
    )
    friend_request_parameters = {
        'requester_id': session['user_id'],
        'requester_name': session['user'],
        'requestee_id': req['requester_id'],
        'requestee_name': req['requester_name'],
    }
    select_icon_query = "SELECT profile_pic FROM users WHERE user_id = %s"
    with db.cursor_context() as cur:
        cur.execute(select_icon_query, (session['user_id'],))
        for row in cur:
            friend_request_parameters['requester_icon'] = row[0]
        cur.execute(friend_request_query, friend_request_parameters)
        for row in cur:
            requestee_name = row[0]
    emit('friend-requested', {'requestee': requestee_name})

@socketio.on('friend-accept', namespace='/socket.io/')
def friend_accept(req):
    '''
    Accept an existing friend request
    (called by the requestee)
    '''
    insert_friend_parameters = {
        'userid1': session['user_id'],
        'userid2': req['user_id'],
        'username1': session['user'],
    }
    select_icon_query = (
        "SELECT profile_pic, username FROM users WHERE user_id = %s"
    )
    with db.cursor_context() as cur:
        cur.execute(select_icon_query, (session['user_id'],))
        for row in cur:
            insert_friend_parameters['icon1'] = row[0]
        cur.execute(select_icon_query, (req['user_id'],))
        for row in cur:
            insert_friend_parameters['icon2'] = row[0]
            insert_friend_parameters['username2'] = row[1]
    insert_friend_query = (
        "INSERT INTO friends "
        "(userid1, username1, icon1, userid2, "
        "username2, icon2, friends_since) "
        "VALUES "
        "(%(userid1)s, %(username1)s, %(icon1)s, %(userid2)s, "
        "%(username2)s, %(icon2)s, now()) "
        "RETURNING username2"
    )
    delete_friend_request_query = (
        "DELETE FROM friend_requests "
        "WHERE (requester_id = %s AND requestee_id = %s) "
        "OR (requestee_id = %s AND requester_id = %s)"
    )
    with db.cursor_context() as cur:
        cur.execute(insert_friend_query, insert_friend_parameters)
        for row in cur:
            requester_name = row[0]
        cur.execute(delete_friend_request_query, (session['user_id'],
                                                  req['user_id'],
                                                  session['user_id'],
                                                  req['user_id']))
    updates = update_awards('friends', user_ids=(session['user_id'],
                                                 req['user_id']))
    emit('friend-accepted', {
        'requester': requester_name,
        'won_awards': updates['won_awards'],
    })

@socketio.on('get-friend-requests', namespace='/socket.io/')
def get_friend_requests(req=None):
    friend_requests = []
    sent = False
    if session and 'user_id' in session:
        if req and 'sent' in req:
            sent = True
            select_friend_requests_query = (
                "SELECT DISTINCT requestee_id, requestee_name "
                "FROM friend_requests WHERE requester_id = %s"
            )
        else:
            select_friend_requests_query = (
                "SELECT DISTINCT requester_id, requester_name, requester_icon "
                "FROM friend_requests WHERE requestee_id = %s"
            )
        with db.cursor_context() as cur:
            cur.execute(select_friend_requests_query, (session['user_id'],))
            for row in cur:
                friend_requests.append(row)
        emit('friend-requests', {
            'friend_requests': friend_requests,
            'sent': sent,
        })

@socketio.on('get-friend-list', namespace='/socket.io/')
def get_friend_list():
    friends = []   
    select_friends_query = (
        "SELECT username1, icon1, username2, icon2 FROM friends "
        "WHERE userid1 = %s OR userid2 = %s"
    )
    with db.cursor_context(True) as cur:
        cur.execute(
            select_friends_query,
            (session['user_id'], session['user_id'])
        )
        for row in cur:
            if row['username1'] == session['user']:
                friends.append([row['username2'], row['icon2']])
            else:
                friends.append([row['username1'], row['icon1']])
    emit('friend-list', {'friends': friends})

@socketio.on('userlist', namespace='/socket.io/')
def userlist():
    userlist = []
    if session and 'user_id' in session:
        select_users_query = (
            "SELECT username, profile_pic FROM users "
            "WHERE username NOT IN ("
            "(SELECT username1 FROM friends "
            "WHERE userid1 = %s or userid2 = %s) "
            "UNION "
            "(SELECT username2 FROM friends "
            "WHERE userid1 = %s OR userid2 = %s)"
            ") ORDER BY active DESC LIMIT 12"
        )
        with db.cursor_context() as cur:
            cur.execute(select_users_query, (session['user_id'],)*4)
            for row in cur:
                userlist.append(row)
    emit('user-listing', {'userlist': userlist})

@socketio.on('populate-scribble', namespace='/socket.io/')
def populate_scribble(req):
    with db.cursor_context(True) as cur:
        query = (
            "SELECT scribbler_name, time_sent, scribble FROM scribble "
            "WHERE scribblee_name = %s "
            "ORDER BY time_sent DESC LIMIT 25"
        )
        cur.execute(query, (req['scribblee'],))
        for row in cur:
            emit('scribble-populate', {
                'user': row['scribbler_name'],
                'timestamp': str(row['time_sent']),
                'comment': row['scribble'],
            })

@socketio.on('scribble', namespace='/socket.io/')
def socket_scribble(message):
    content = {
        'scribbler_id': session['user_id'],
        'scribbler_name': session['user'],
        'scribblee_id': message['scribblee_id'],
        'scribblee_name': message['scribblee_name'],
        'scribble': message['data'],
    }
    query = (
        "INSERT INTO scribble "
        "(scribbler_id, scribblee_id, scribbler_name, "
        "scribblee_name, time_sent, scribble) "
        "VALUES "
        "(%(scribbler_id)s, %(scribblee_id)s, %(scribbler_name)s, "
        "%(scribblee_name)s, now(), %(scribble)s) "
        "RETURNING scribbler_name"
    )
    with db.cursor_context() as cur:
        cur.execute(query, content)
    if message['data']:
        emit('scribble-response', {
            'data': message['data'],
            'user': content['scribbler_name'],
        }, broadcast=True)

@socketio.on('populate-chatbox', namespace='/socket.io/')
def populate_chatbox():
    with db.cursor_context(True) as cur:
        query = (
            "SELECT * FROM ("
            "SELECT username, time_sent, comment FROM chatbox "
            "ORDER BY time_sent DESC LIMIT 6) s "
            "ORDER BY time_sent ASC"
        )
        cur.execute(query)
        for row in cur:
            emit('chat-populate', {
                'user': row['username'],
                'timestamp': str(row['time_sent']),
                'comment': row['comment'],
            })

@socketio.on('chat', namespace='/socket.io/')
def socket_message(message):
    content = {
        'user_id': session['user_id'] if 'user_id' in session else None,
        'username': session['user'] if 'user' in session else 'Guest',
        'comment': message['data'],
    }
    query = (
        "INSERT INTO chatbox (user_id, username, time_sent, comment) "
        "VALUES (%(user_id)s, %(username)s, now(), %(comment)s)"
    )
    with db.cursor_context() as cur:
        cur.execute(query, content)
    if message['data']:
        emit('chat-response', {
            'data': message['data'],
            'user': content['username'],
        }, broadcast=True)

@socketio.on('request-chart-data', namespace='/socket.io/')
def charts(req):
    '''
    Fetch resampled price time series and send to the front-end for display
    using the HighChart/HighStock library.  Signal resampling is carried out
    in Spork.resampler (Ripple Charts API).
    TODO: Change altcoin data inflow from Spork.resampler to either use
          (1) BitcoinAverage/CryptoCoinCharts API data from Pricer, or
          (2) Real-time ledger closings on local rippled from Grapple.
    '''
    freq = req['freq']
    currency1 = req['currency1']
    currency2 = req['currency2']
    data = []
    currency_name = ''
    with db.cursor_context() as cur:
        query = (
            "SELECT starttime, open1, high1, low1, close1 "
            "FROM resampled "
            "WHERE freq = %s AND currency1 = %s AND currency2 = %s"
        )
        cur.execute(query, (freq, currency1, currency2))
        for row in cur:
            data.append([float(r) if i else r for i, r in enumerate(row)])
        query2 = "SELECT name FROM currencies WHERE symbol = %s"
        named_currency = currency1 if currency1 != 'USD' else currency2
        cur.execute(query2, (named_currency,))
        for row in cur:
            currency_name = row[0]
    emit('chart-data', {'data': data, 'name': currency_name})

@socketio.on('connect', namespace='/socket.io/')
def socket_connect():
    if app.config['TESTING']:
        guard = Guard()
        login_info = {
            'username': app.config['TESTUSER'],
            'password': app.config['TESTPASS'],
        }
        query = (
            "SELECT user_id, email, walletaddress, walletsecret, iv, admin "
            "FROM users WHERE username = %s"
        )
        user_data = None
        with db.cursor_context(True) as cur:
            cur.execute(query, (login_info['username'],))
            user_data = cur.fetchone()
        if user_data is not None:
            user = User(user_data['user_id'],
                        login_info['username'],
                        user_data['email'],
                        user_data['walletaddress'],
                        base64.b64decode(user_data['walletsecret']),
                        base64.b64decode(user_data['iv']))
            login_user(user)
            session['user'] = escape(user.username)
            session['address'] = escape(user.wallet_address)
            session['secret'] = guard.AES_clear(user.encrypted_secret,
                                                login_info['password'],
                                                user.encrypted_iv)
            session['admin'] = user_data['admin']
    else:
        print "Client connected"

@socketio.on('disconnect', namespace='/socket.io/')
def socket_disconnect():
    if app.config['TESTING']:
        logout_user()
        session.pop('user', None)
        session.pop('user_id', None)
        session.pop('address', None)
        session.pop('secret', None)
        session.pop('admin', None)
        del guard
    else:
        print "Client disconnected"
