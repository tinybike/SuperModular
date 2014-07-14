#!/usr/bin/env python

from __future__ import division

import json, datetime
from decimal import *

from dyffy import app

from flask import session, request, escape, url_for, redirect, render_template, g
from flask.ext.security import current_user, login_required, SQLAlchemyUserDatastore, Security
from flask.ext.security.signals import user_registered
from flask.ext.security.utils import login_user, logout_user, get_hmac
from werkzeug import secure_filename

from dyffy.models import db, User, Role


# setup flask-security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# pre-request setup
@app.before_request
def before_request():

    g.user = current_user


@app.route('/')
def home():

    return render_template('home.html')


@app.route('/play')
def play():

    return render_template('play.html')


@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = user_datastore.create_user(username=username, email=email, password=get_hmac(password))
        db.session.commit()

        # create wallet
        user.create_wallet()

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

        user = user_datastore.find_user(username=username, password=get_hmac(password))

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


@app.route("/profile/<username>")
@login_required
def profile(username):

    return render_template('profile.html')
