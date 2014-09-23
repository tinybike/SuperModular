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

    return d

@socketio.on('game:read', namespace='/socket.io/')
def game(data):

    app.logger.info(data)
    game = Game.query.get(data['id'])
    game.bets.all();

    if game:
        
        emit('game:update', to_dict(game))


@socketio.on('open-games:read', namespace='/socket.io/')
def open_games(data):

    open_games = [to_dict(game) for game in Game.query.filter(Game.no_more_bets != True).all()]

    emit('open-games:update', open_games)


@socketio.on('my-games:read', namespace='/socket.io/')
def my_games(data):

    if current_user.is_authenticated():

        my_games = [to_dict(game) for game in Game.query.filter(Game.players.any(id=current_user.id)).filter_by(finished=None).all()]

        app.logger.info(my_games)

        emit('my-games:update', my_games)


@socketio.on('recent-games:read', namespace='/socket.io/')
def recent_games(data):

    recent_games = [to_dict(game) for game in Game.query.filter(Game.finished != None).order_by('finished').all()]

    app.logger.info(recent_games)

    emit('recent-games:update', recent_games)


@socketio.on('wallet:read', namespace='/socket.io/')
def wallet(data):

    if current_user.is_authenticated():

        emit('wallet:update', [
            {'currency': 'dyf', 'balance': str(current_user.wallet.dyf_balance)}
        ])


@socketio.on('finish-game', namespace='/socket.io/')
def finish_game(data):

    g = Game.query.get(data['game_id'])

    if g.finished:

        emit('wallet:update', [
            {'currency': 'dyf', 'balance': str(current_user.wallet.dyf_balance)}
        ])

    else:

        app.logger.info("game %s hasn't finished yet" % g.id)


@socketio.on('friends:read', namespace='/socket.io/')
def friends(data):

    if current_user.is_authenticated():

        friends, others = current_user.get_friends()

        app.logger.info(friends)

        emit('friends:update', friends)


@socketio.on('others:read', namespace='/socket.io/')
def others(data):

    if current_user.is_authenticated():

        friends, others = current_user.get_friends()

        emit('others:update', others)


@socketio.on('friend-request', namespace='/socket.io/')
def friend_request(data):

    if current_user.is_authenticated() and current_user.request_friend(data['user_id']):

        friends, others = current_user.get_friends()
        response = {'friends': friends, 'others': others}

        emit('friend-list', response)

    else:

        emit('friend-requested', {'error': 'unknown user'})


@socketio.on('friend-accept', namespace='/socket.io/')
def friend_accept(data):

    if current_user.is_authenticated():

        friend = Friend.query.filter_by(user1_id=data['user_id'], user2_id=current_user.id).first()

        if friend:

            friend.accept()

            friends, others = current_user.get_friends()
            response = {'friends': friends, 'others': others}

        else:

            response = {'error': 'unknown friend request'}

        app.logger.info('accepting %s', message['user_id'])
        
        emit('friend-list', response)


@socketio.on('friend-reject', namespace='/socket.io/')
def friend_reject(data):

    if current_user.is_authenticated():

        friend = Friend.query.filter_by(user1_id=data['user_id'], user2_id=current_user.id).first()

        if friend:

            friend.reject()

            friends, others = current_user.get_friends()
            response = {'friends': friends, 'others': others}

        else:

            response = {'error': 'unknown friend request'}

        app.logger.info('rejecting %s', message['user_id'])
        
        emit('friend-list', response)


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
def chat(data):

    if current_user.is_authenticated():

        c = Chat(author=current_user.username, comment=data['data'], timestamp=datetime.datetime.now())

        db.session.add(c)
        db.session.commit()

        chat = {'author': c.author, 'comment': c.comment, 'timestamp': datetime.datetime.strftime(c.timestamp, "%Y-%m-%d %H:%M:%S")}

        emit('chat', {'chat': [chat]}, broadcast=True)


@socketio.on('bet', namespace='/socket.io/')
def bet(data):

    if current_user.is_authenticated():

        # TODO: develop better gametype lookup
        game = Game.query.get(data['game_id'])
        if game and game.name == 'parimutuel-dice':
            game = Parimutuel.query.get(data['game_id'])
        elif game and game.name == 'soundcloud':
            game = Jellybeans.query.get(data['game_id'])
        else:
            app.logger.error('no game found')
            return
        
        if not game.no_more_bets:

            guess, amount = game.bet(current_user, data['guess'], data['amount'])

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
