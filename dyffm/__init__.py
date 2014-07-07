from gevent import monkey
monkey.patch_all()

import os
from flask import Flask
from flask.ext.socketio import SocketIO

app = Flask(__name__)
app.config.from_object('dyffy.config')

socketio = SocketIO(app)

from dyffy import routes
from dyffy import sockets 
from dyffy.utils import *

timing_loop(round_complete)
