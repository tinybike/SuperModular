#!/usr/bin/env python
from dyffy import app

import os, subprocess, urllib

from flask import url_for
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
        if db.engine.name == 'postgresql':
            db.engine.execute("drop schema if exists public cascade")
            db.engine.execute("create schema public")
        else:
            db.drop_all()
        db.create_all()

manager.add_command("initdb", InitDB())

@manager.command
def listroutes():
    "list all routes"

    output = []

    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = urllib.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
        output.append(line)
    
    for line in sorted(output):
        print line


@manager.shell
def make_shell_context():
    """
    creates a python REPL with several default imports
    in the context of the app
    """
    return dict(app=app, db=db)


if __name__ == "__main__":
    manager.run()
