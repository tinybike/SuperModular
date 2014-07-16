# main dyffy config
import os, platform, sys

SECRET_KEY = os.environ.get('SECRET_KEY')
DEPLOY_ENV = os.environ.get('DEPLOY_ENV', 'local')
DEBUG = True if 'DEBUG' in os.environ and os.environ['DEBUG'] == 'true' else False

# setup postgres from os env
SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')

# BTC setup
BITCOIND_HOST = os.environ.get('BITCOIND_HOST')
BITCOIND_USERNAME = os.environ.get('BITCOIND_USERNAME')
BITCOIND_PASSWORD = os.environ.get('BITCOIND_PASSWORD')

TESTING = False

# threshold for betting markets to close unchanged/neutral
NEUTRAL_THRESHOLD = 1e-07

# user uploaded media
UPLOAD_FOLDER = './uploads'
MAX_CONTENT_LENGTH =  10000000

# social logins
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')

# use local config for development environments
if DEPLOY_ENV != 'prod':
    DEBUG = True
    try:
        from config_local import *
    except ImportError:
        print '\nYou must create a config_local.py file for local development.\n'
