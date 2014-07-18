#!/usr/bin/env python

from __future__ import division

import json, datetime
from decimal import *

from dyffy import app

from flask import session, request, escape, url_for, redirect, render_template, g
from flask_oauthlib.client import OAuth, OAuthException
from flask.ext.login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug import secure_filename

from dyffy.models import db, User

import requests

# flask-login
login_manager = LoginManager(app)
login_manager.session_protection = "basic"
login_manager.login_view = "/login"


oauth = OAuth(app)

facebook = oauth.remote_app(
    'facebook',
    consumer_key=app.config['FACEBOOK_APP_ID'],
    consumer_secret=app.config['FACEBOOK_APP_SECRET'],
    request_token_params={'scope': 'email'},
    base_url='https://graph.facebook.com',
    request_token_url=None,
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth'
)


@app.route('/login/facebook')
def facebook_login():

    callback = url_for(
        'facebook_authorized',
        next = request.args.get('next') or request.referrer or None, _external=True
    )

    return facebook.authorize(callback=callback)


@app.route('/login/facebook/authorized')
@facebook.authorized_handler
def facebook_authorized(response):

    if response is None:

        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )

    if isinstance(response, OAuthException):

        return 'Access denied: %s' % response.message

    app.logger.info(response['access_token'])

    session['oauth_token'] = (response['access_token'], '')
    me = facebook.get('/me')

    app.logger.info(me.data)

    user = User.get_user(facebook_id=me.data['id'])

    # create new user if one doesn't exist
    if not user:
        avatar = 'http://graph.facebook.com/{0}/picture'.format(me.data['id'])
        user = User.create_user(facebook_id=me.data['id'], facebook_access_token=response['access_token'], name=me.data['name'], avatar=avatar)

    login_user(user)

    return redirect(url_for('home'))


@facebook.tokengetter
def get_facebook_oauth_token():
    return session.get('oauth_token')




@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)


# pre-request setup
@app.before_request
def before_request():

    g.user = current_user

    if current_user.is_authenticated():
        g.friends, g.others = current_user.get_friends()


@app.route('/')
def home():

    return render_template('home.html')


@app.route('/play')
def play():

    game = {}

    return render_template('play.html', game=game)


@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = User.create_user(username=username, password=password, email=email)

        login_user(user)

        return redirect(url_for('home'))

    else:

        return render_template('register.html')


@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False

        user = User.get_user(username=username, password=password)

        if user:

            login_user(user, remember=remember)

            return redirect(url_for('home'))

        else:

            app.logger.error('> failed login attempt for {0}'.format(username))
            return render_template('login.html')

    else:

        return render_template('login.html')


@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('home'))


@app.route("/profile/<user_id>")
def profile(user_id):

    user = User.query.get(user_id)

    if user:
        return render_template('profile.html', user=user)
    else:
        return redirect(url_for('home'))
