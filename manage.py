#!/usr/bin/env python
from dyffy import app

import os, subprocess

from flask.ext.script import Manager, Command, Option

from dyffy import socketio
from dyffy.models import db

manager = Manager(app)

class Server(Command):
    "run gevent-socketio server"
    
    option_list = (
        Option('--host', '-h', dest='host'),
        Option('--port', '-p', dest='port'),
    )
    
    def run(self, host, port):
        if host:
            socketio.run(app, host=host, port=int(port))
        else:
            socketio.run(app)

manager.add_command("runserver", Server())


class InitDB(Command):
    "initialize database"
    
    def run(self):
        db.drop_all()
        db.create_all()

manager.add_command("initdb", InitDB())


@manager.shell
def make_shell_context():
    """
    Creates a python REPL with several default imports
    in the context of the app
    """
    return dict(app=app, db=db)

if __name__ == "__main__":
    manager.run()
