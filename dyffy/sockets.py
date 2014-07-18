#!/usr/bin/env python

from __future__ import division

import base64, datetime

from dyffy import app
from dyffy import socketio

from flask import session, escape, g
from flask.ext.login import current_user, login_user, logout_user
from flask.ext.socketio import emit

from dyffy.models import db, User, Friend, Chat
from babbage import Jellybeans


@socketio.on('get-wallet', namespace='/socket.io/')
def get_wallet_balance():

    if current_user.is_authenticated():

        wallet = current_user.wallet

        if wallet:

            emit('balance', {
                'dyf': str(wallet.dyf_balance),
                'btc': str(wallet.btc_balance)
            })


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

        jb = Jellybeans(current_user.id)
        
        if not jb.game.has_bet(current_user.id):

            jb.bet(current_user.id, message['guess'])

            emit('balance', {'dyf': str(current_user.wallet.dyf_balance)})

            emit('add-bet', {
                'game_id': jb.game.id, 
                'bet': {
                    'user': {
                        'username': current_user.username,
                        'id': current_user.id
                    }, 
                'guess': message['guess'], 
                'amount': 10
                }
            }, broadcast=True)

            emit('no-more-bets')

            if jb.game.started:

                 emit('start-game', {'start_time': datetime.datetime.strftime(jb.game.started, "%Y-%m-%d %H:%M:%S")})



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
