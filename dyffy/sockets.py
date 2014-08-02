#!/usr/bin/env python

from __future__ import division

import base64, datetime, json, decimal

from dyffy import app
from dyffy import socketio

from flask import session, escape, g
from flask.ext.login import current_user, login_user, logout_user
from flask.ext.socketio import emit, send

from dyffy.models import db, User, Friend, Chat, Game
from babbage import Jellybeans, Parimutuel


# flattens a model for json output
def to_dict(model):

    d = dict((prop, getattr(model, prop)) for prop in model.__table__.columns.keys())
    if hasattr(model, 'bets'):
        d['bets'] = [to_dict(bet) for bet in model.bets]
        app.logger.info(d['bets'])

    return d

@socketio.on('game:read', namespace='/socket.io/')
def get_game(data):

    app.logger.info(data)
    game = Game.query.get(data['id'])
    game.bets.all();

    if game:
        
        emit('game:update', to_dict(game))


@socketio.on('open-games:read', namespace='/socket.io/')
def get_open_games(data):

    open_games = [to_dict(game) for game in Game.query.filter(Game.no_more_bets != True).all()]

    app.logger.info(open_games)

    emit('open-games:update', open_games)


@socketio.on('my-games:read', namespace='/socket.io/')
def get_my_games(data):

    my_games = [to_dict(game) for game in Game.query.filter(Game.players.any(id=current_user.id)).filter_by(finished=None).all()]

    app.logger.info(my_games)

    emit('my-games:update', my_games)


@socketio.on('recent-games:read', namespace='/socket.io/')
def get_recent_games(data):

    recent_games = [to_dict(game) for game in Game.query.filter(Game.finished != None).order_by('finished').all()]

    app.logger.info(recent_games)

    emit('recent-games:update', recent_games)


@socketio.on('get-wallet', namespace='/socket.io/')
def get_wallet_balance():

    if current_user.is_authenticated():

        wallet = current_user.wallet

        if wallet:

            pass


@socketio.on('finish-game', namespace='/socket.io/')
def finish_game(message):

    g = Game.query.get(message['game_id'])

    if g.finished:

        emit('balance', {
            'dyf': str(current_user.wallet.dyf_balance),
            'btc': str(current_user.wallet.btc_balance)
        })

    else:

        app.logger.info("game %s hasn't finished yet" % g.id)


@socketio.on('friend-request', namespace='/socket.io/')
def friend_request(message):

    if current_user.is_authenticated() and current_user.request_friend(message['user_id']):

        friends, others = current_user.get_friends()
        response = {'friends': friends, 'others': others}

        emit('friend-list', response)

    else:

        emit('friend-requested', {'error': 'unknown user'})


@socketio.on('friend-accept', namespace='/socket.io/')
def friend_accept(message):

    if current_user.is_authenticated():

        friend = Friend.query.filter_by(user1_id=message['user_id'], user2_id=current_user.id).first()

        if friend:

            friend.accept()

            friends, others = current_user.get_friends()
            response = {'friends': friends, 'others': others}

        else:

            response = {'error': 'unknown friend request'}

        app.logger.info('accepting %s', message['user_id'])
        
        emit('friend-list', response)


@socketio.on('friend-reject', namespace='/socket.io/')
def friend_reject(message):

    if current_user.is_authenticated():

        friend = Friend.query.filter_by(user1_id=message['user_id'], user2_id=current_user.id).first()

        if friend:

            friend.reject()

            friends, others = current_user.get_friends()
            response = {'friends': friends, 'others': others}

        else:

            response = {'error': 'unknown friend request'}

        app.logger.info('rejecting %s', message['user_id'])
        
        emit('friend-list', response)


@socketio.on('get-friends', namespace='/socket.io/')
def get_friends():

    if current_user.is_authenticated():

        friends, others = current_user.get_friends()

        emit('friend-list', {'friends': friends, 'others': others})


@socketio.on('get-chats', namespace='/socket.io/')
def get_chats():

    if current_user.is_authenticated():

        chat = []

        for c in Chat.query.order_by(Chat.timestamp).limit(20).all():

            chat.append({
                'author': c.author,
                'comment': c.comment,
                'timestamp': datetime.datetime.strftime(c.timestamp, "%Y-%m-%d %H:%M:%S")
            })

        emit('chat', {'chat': chat})


@socketio.on('chat', namespace='/socket.io/')
def chat(message):

    if current_user.is_authenticated():

        c = Chat(author=current_user.username, comment=message['data'], timestamp=datetime.datetime.now())

        db.session.add(c)
        db.session.commit()

        chat = {'author': c.author, 'comment': c.comment, 'timestamp': datetime.datetime.strftime(c.timestamp, "%Y-%m-%d %H:%M:%S")}

        emit('chat', {'chat': [chat]}, broadcast=True)


@socketio.on('bet', namespace='/socket.io/')
def bet(message):

    if current_user.is_authenticated():

        # TODO: develop better gametype lookup
        game = Game.query.get(message['game_id'])
        if game and game.name == 'parimutuel-dice':
            game = Parimutuel.query.get(message['game_id'])
        elif game and game.name == 'soundcloud':
            game = Jellybeans.query.get(message['game_id'])
        else:
            app.logger.error('no game found')
            return
        
        if not game.no_more_bets:

            guess, amount = game.bet(current_user, message['guess'], message['amount'])

            emit('balance', {'dyf': str(current_user.wallet.dyf_balance)})

            emit('add-bet', {
                'game_id': game.id, 
                'bet': {
                    'user': {
                        'username': current_user.username,
                        'id': current_user.id
                    }, 
                'guess': guess, 
                'amount':  amount
                }
            }, broadcast=True)

            if game.no_more_bets:

                emit('no-more-bets', {'game_id': game.id}, broadcast=True)

            if game.started:

                emit('start-game', {
                    'current_time': datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S"),
                    'end_time': datetime.datetime.strftime(game.ends_at, "%Y-%m-%d %H:%M:%S"),
                    'id': game.id
                }, broadcast=True)

                
@socketio.on('connect', namespace='/socket.io/')
def socket_connect():

    if app.config['TESTING']:

        # TODO: reimplement testing code
        pass

    else:

        app.logger.info("[websocket] client connected")


@socketio.on('disconnect', namespace='/socket.io/')
def socket_disconnect():

    if app.config['TESTING']:

        # TODO: reimplement testing code
        pass

    else:
         
        app.logger.info("[websocket] client disconnected")
