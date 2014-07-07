#!/usr/bin/env python

"""
CryptoCab/Dyffy back-end core.
(c) Jack Peterson (jack@tinybike.net), 4/19/2014
"""

from __future__ import division

import json, datetime, base64
from decimal import *

from flask import session, request, escape, flash, url_for, redirect, render_template, g, send_from_directory
from flask.ext.login import login_user, logout_user, current_user, login_required, LoginManager
from werkzeug import secure_filename

from dyffy.models import User
from dyffy.guard import Guard
from dyffy.pricer import Pricer
from dyffy.utils import *

from dyffy import app
from dyffy import db

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

guard = Guard()

#########
# Index #
#########

@app.route('/')
def index():
    return render_template('index.html')

############
# Register #
############

def check_username_taken(requested_username):
    with db.cursor_context() as cur:
        cur.execute("SELECT count(*) FROM users WHERE username = %s",
                    (requested_username,))
        if cur.rowcount:
            username_taken = cur.fetchone()[0]
    if username_taken > 0:
        return True
    return False

def insert_user(username, password, email, wallet, secret):
    dyff_freebie = '100'
    encrypted_secret, iv = guard.AES_cipher(secret, password)
    insert_user_parameters = {
        'username': username,
        'password': guard.bcrypt_digest(password.encode('utf-8')),
        'email': email,
        'walletaddress': wallet,
        'walletsecret': base64.b64encode(encrypted_secret),
        'iv': base64.b64encode(iv),
    }
    insert_user_query = (
        "INSERT INTO users "
        "(username, password, email, joined, walletaddress, "
        "walletsecret, iv, profile_pic) "
        "VALUES "
        "(%(username)s, %(password)s, %(email)s, now(), %(walletaddress)s, "
        "%(walletsecret)s, %(iv)s, 'cyclicoin.png') "
        "RETURNING user_id"
    )
    insert_result = None
    with db.cursor_context() as cur:
        cur.execute(insert_user_query, insert_user_parameters)
        if cur.rowcount:
            insert_result = cur.fetchone()[0]
    return insert_result, encrypted_secret, iv

def create_session(userid, username, password, email, wallet, secret, iv):
    user = User(userid, username, email, wallet, secret, iv)
    login_user(user)
    session['user'] = escape(user.username)
    session['address'] = escape(user.wallet_address)
    session['secret'] = guard.AES_clear(secret, password, iv)
    # TODO initial tracking table inserts
    return user, session

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    if not check_username_taken(request.form['username']):
        insert_result, encrypted_secret, iv = insert_user(
            request.form['username'],
            request.form['password'],
            request.form['email'],
            request.form['new-wallet'],
            request.form['new-secret']
        )
        # Success
        if insert_result is not None:
            user, session = create_session(insert_result,
                                           request.form['username'],
                                           request.form['password'],
                                           request.form['email'],
                                           request.form['new-wallet'],
                                           encrypted_secret,
                                           iv)
            return render_template('index.html', registration_ok=True)
        # Failure
        else:
            user = None
            return render_template('index.html', registration_ok=False)
    else:
        print "Username", request.form['username'], "taken"
        return render_template('register.html', err="Username taken")

#########
# Login #
#########

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('index'))
        else:
            return render_template('login.html')
    user = None
    with db.cursor_context(True) as cur:
        query = (
            "SELECT user_id, password, email, walletaddress, "
            "walletsecret, iv, admin FROM users "
            "WHERE username = %s"
        )
        cur.execute(query, (request.form['username'],))
        for row in cur:
            stored_password_digest = row['password']
            if guard.check_password(request.form['password'].encode('utf-8'), 
                                    stored_password_digest):
                try:
                    encrypted_secret = base64.b64decode(row['walletsecret'])
                    iv = base64.b64decode(row['iv'])
                except TypeError:
                    encrypted_secret = row['walletsecret']
                    iv = row['iv']
                user = User(row['user_id'],
                            request.form['username'],
                            row['email'],
                            row['walletaddress'],
                            encrypted_secret,
                            iv)
                admin = row['admin']
    if user is None or user.id is None:
        flash('Username or password is invalid', 'error')
        return redirect(url_for('login'))
    with db.cursor_context() as cur:
        query = "UPDATE users SET active = now() WHERE user_id = %s"
        cur.execute(query, (user.id,))
    if 'remember' in request.form and request.form['remember'] == 'Y':
        login_user(user, remember=True)
    else:
        login_user(user)
    session['user'] = escape(user.username)
    session['address'] = escape(user.wallet_address)
    session['secret'] = guard.AES_clear(encrypted_secret,
                                        request.form['password'],
                                        iv)
    session['admin'] = admin
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('address', None)
    session.pop('secret', None)
    session.pop('admin', None)
    return redirect(url_for('index'))

@login_manager.user_loader
def load_user(user_id):
    user = None
    query = "SELECT user_id, username, email FROM users WHERE user_id = %s"
    with db.cursor_context(True) as cur:
        cur.execute(query, (str(user_id),))
        if cur.rowcount:
            res = cur.fetchone()
            user = User(res['user_id'], res['username'], res['email'])
    return user

##########
# Upload #
##########

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and guard.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

############
# Advanced #
############

@app.route('/advanced')
def advanced():
    return render_template('advanced.html')

###########
# The Bar #
###########
# FB API:
# 1. Get randomly selected profile pic of user's friends
# 2. Rate hotness
# 3. You get money if your ranking syncs up with others'!
@app.route('/bar')
@login_required
def bar():
    fb_connect = 0
    if session and 'user' in session:
        select_user_query = (
            "SELECT count(*) FROM users "
            "WHERE username = %s AND fb_connect = 't'"
        )
        with db.cursor_context() as cur:
            cur.execute(select_user_query, (session['user'],))
            fb_connect = cur.fetchone()[0]
    return render_template('bar.html', fb_connect=fb_connect)

@app.before_request
def before_request():
    g.user = current_user
    g.debug = True if app.debug else False

###########
# Profile #
###########

@app.route("/settings")
@login_required
def settings():
    return redirect(url_for('index'))

@app.route("/profile/<username>")
@login_required
def profile(username):
    data = {'profile_pic': 'cyclicoin.png'}
    if 'user_id' in session:
        query = "SELECT * FROM users WHERE username = %s"
        with db.cursor_context(True) as cur:
            cur.execute(query, (username,))
            user_info = cur.fetchone()
        if user_info['firstname'] is not None and user_info['lastname'] is not None:
            full_name = user_info['firstname'] + ' ' + user_info['lastname']
        else:
            full_name = None
        if user_info is not None:
            profile_pic = user_info['profile_pic'] if user_info['profile_pic'] is not None else 'cyclicoin.png'
            data = {
                'user_id': user_info['user_id'],
                'username': username,
                'full_name': full_name,
                'gender': user_info['gender'],
                'birthday': user_info['birthday'],
                'age': user_info['age'],
                'location': user_info['location'],
                'walletaddress': user_info['walletaddress'],
                'bitcoin_external': user_info['bitcoin_external'],
                'ripple_external': user_info['ripple_external'],
                'dogecoin_external': user_info['dogecoin_external'],
                'netcoin_external': user_info['netcoin_external'],
                'linkedin_url': user_info['linkedin_url'],
                'facebook_url': user_info['facebook_url'],
                'twitter_url': user_info['twitter_url'],
                'google_url': user_info['google_url'],
                'profile_pic': profile_pic,
                'joined': str(user_info['joined']).split(' ')[0],
                'active': str(user_info['active']).split(' ')[0],
            }
    return render_template('profile.html', **data)
