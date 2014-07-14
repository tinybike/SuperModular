#!/usr/bin/env python

from __future__ import division

import base64, datetime

from dyffy import app
from dyffy import socketio

from flask import session, escape, g
from flask.ext.security import current_user
from flask.ext.security.utils import login_user, logout_user
from flask.ext.socketio import emit

from dyffy.models import db, User, Friend, Chat


@socketio.on('get-wallet-balance', namespace='/socket.io/')
def get_wallet_balance():

    if current_user.is_authenticated():

        wallet = current_user.wallet

        if wallet:

            emit('wallet-balance', {
                'dyf': wallet.dyf_balance,
                'btc': wallet.btc_balance
            })


@socketio.on('friend-request', namespace='/socket.io/')
def friend_request(message):

    if current_user.is_authenticated() and current_user.request_friend(message['user_id']):

        emit('friend-requested', {})

    else:

        emit('friend-requested', {'error': 'unknown user'})


@socketio.on('friend-accept', namespace='/socket.io/')
def friend_accept(message):

    if current_user.is_authenticated():

        friend = Friend.query.filter_by(user_id=current_user.id, friend_id=message['user_id']).first()

        if friend:

            friend.acccept()

            response = {}

        else:

            response = {'error': 'unknown friend request'}
        
        emit('friend-accepted', response)


@socketio.on('get-friends', namespace='/socket.io/')
def get_friends():

    if current_user.is_authenticated():

        friends = []

        for f in current_user.get_friends():

            friends.append({
                'id': f.id,
                'username': f.username,
                'avatar': f.avatar,
                'last_on': u.last_login
            })

        emit('friend-list', {'friends': friends})


@socketio.on('user-list', namespace='/socket.io/')
def user_list():

    if current_user.is_authenticated():

        users = []

        for u in User.query.all():

            users.append({
                'id': u.id,
                'username': u.username,
                'avatar': u.avatar,
                'last_on': u.last_login
            })


        emit('user-list', {'user_list': users})


@socketio.on('get-chat', namespace='/socket.io/')
def get_chat():

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
