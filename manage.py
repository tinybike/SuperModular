#!/usr/bin/env python
import os, subprocess

from flask.ext.script import Manager, Command, Option

from dyffy import app
from dyffy import socketio

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

@manager.shell
def make_shell_context():
    """
    Creates a python REPL with several default imports
    in the context of the app
    """
    return dict(app=app, User=User)

@manager.command
def dbsetup():
    from dyffy import db
    from dyffy.spork import Spork
    from dyffy.pricer import Pricer
    get_ripple_history = False
    pricer = Pricer(full=True, verbose=True)
    db.currencies()
    if get_ripple_history:
        spork = Spork(**{
            'num_results': 1000,
            'base_url': 'https://ripple.com/chart/',
            'json_suffix': '/trades.json?since=',
            'socket_url': 'wss://s1.ripple.com:51233/',
        })
        db.history()
        db.resample()
        spork.ripple_tables()
        spork.ripple()
        spork.resample()
    db.altcoin_cfd_tables()
    db.triggers()
    pricer.update_data()

@manager.command
def compilestatic():
    """Compile static files with java based closure-compile"""
    s = "java -jar compiler.jar --compilation_level SIMPLE_OPTIMIZATIONS --js dyffy/static/js/cab.js --js_output_file dyffy/static/js/cab-compiled.js"
    fs = "java -jar compiler.jar --compilation_level SIMPLE_OPTIMIZATIONS --js dyffy/static/js/foundation/foundation.js --js dyffy/static/js/foundation/foundation.topbar.js --js dyffy/static/js/foundation/foundation.tab.js --js dyffy/static/js/foundation/foundation.dropdown.js --js dyffy/static/js/foundation/foundation.reveal.js --js_output_file dyffy/static/js/foundation-compiled.js" 
    subprocess.call(s, shell=True)
    subprocess.call(fs, shell=True)

@manager.command
def pricer():
    """Update third-party coin price data"""
    subprocess.call("nohup python dyffy/pricer.py > p.out 2> p.err < /dev/null &", shell=True)

@manager.command
def clonedb():
    """Clone production db for local development"""
    cmd = "ssh deploy@crypto.cab 'sudo -u postgres pg_dumpall' > /tmp/db.dump"
    print "Dumping production DB to /tmp/db.dump ..."
    subprocess.call(cmd, shell=True)
    print "Loading /tmp/db.dump ..."
    cmd = "psql -f /tmp/db.dump"
    subprocess.call(cmd, shell=True)

if __name__ == "__main__":
    manager.run()
