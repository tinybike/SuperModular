# main dyffy config
import os, platform, sys

SECRET_KEY = os.environ.get('SECRET_KEY')
DEPLOY_ENV = os.environ.get('DEPLOY_ENV', 'local')
DEBUG = True if 'DEBUG' in os.environ and os.environ['DEBUG'] == 'true' else False

# setup postgres from os env
SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')

# flask-security
SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
SECURITY_LOGIN_URL = '/foo1'    #    
SECURITY_LOGOUT_URL = '/foo2'   # pushing flask-sec's packaged views out of way for now
SECURITY_REGISTER_URL = '/foo3' #

TESTING = False

# threshold for betting markets to close unchanged/neutral
NEUTRAL_THRESHOLD = 1e-07

# tables storing users' bets for the current round
BET_TABLES = ('altcoin_bets', 'altcoin_vs_bets')

# user uploaded media
UPLOAD_FOLDER = './uploads'
MAX_CONTENT_LENGTH =  10000000

# use local config for development environments
if DEPLOY_ENV != 'prod':
    DEBUG = True
    try:
        from config_local import *
    except ImportError:
        print '\nYou must create a config_local.py file for local development.\n'
