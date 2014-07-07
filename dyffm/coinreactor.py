#!/usr/bin/env python
"""
Coin bridges and listeners
"""
import sys
import requests
import psycopg2, psycopg2.extensions

from flask.ext.socketio import emit
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bunch import Bunch

from dyffy import db

class CoinReactor(object):

    def __init__(self, coin_code):
        self.coin_code = coin_code
        self.connected = False
        self.verified = False
        self.profile = None

    def RPC_connect(self):
        query = (
            "SELECT name, rpc, confirmations, blockchain, homepage, description "
            "FROM issued_coins WHERE code = %s"
        )
        with db.cursor_context(True) as cur:
            cur.execute(query, self.coin_code)
            for row in cur:
                RPCurl = row['rpc']
                self.profile = Bunch({
                    'name': row['name'],
                    'confirmations': row['confirmations'],
                    'blockchain': row['blockchain'],
                    'homepage': row['homepage'],
                    'description': row['description'],
                })
        self.RPC = AuthServiceProxy(RPCurl)
        self.connected = True

    def verify_blockcount(self):
        try:
            local_blockcount = self.RPC.getblockcount()
        except JSONRPCException as e:
            return "Error connecting to coin daemon:", e
        else:
            try:
                remote_blockcount = requests.get(self.profile.blockchain + \
                                                 "q/getblockcount").json()
            except requests.ConnectionError as e:
                return "Unable to get count from blockexplorer:"+str(e)
            else:
                if (int(remote_blockcount) - 5) > local_blockcount:
                    return "Blockchain not up to date: true block count is: " + \
                        str(remote_blockcount) + ", while dogecoind is at: " + \
                        str(local_blockcount)
                else:
                    return True

    def bridge(self, user_id, amount, currency, address, direction,
               confirmations=0, confirmed=False):
        # direction is either "d" for deposit or "w" for withdrawal
        parameters = {
            'user_id': user_id,
            'amount': amount,
            'currency': currency,
            'address': address,
            'direction': direction,
            'confirmations': confirmations,
            'confirmed': confirmed,
        }
        query = (
            "INSERT INTO bridge_ledger "
            "(user_id, txdate, amount, currency, address, direction) "
            "VALUES "
            "(%(user_id)s, now(), %(amount)s, %(currency)s, %(address)s, "
            "%(direction)s, %(confirmations)s, %(confirmed)s)"
        )
        with db.cursor_context() as cur:
            cur.execute(query, parameters)
        target = 'bridge-deposit' if direction == 'd' else 'bridge-withdrawal'
        # check that we've sent/received coins
        self.listen(currency, address)
        emit(target, {'amount': amount, 'currency': currency})

    def listen(self):
        with db.cursor_context() as cur:
            cur.execute("LISTEN confirmation")

    def receive(self, fd, events):
        try:
            connection = db.connect()
            state = connection.poll()
            if state == psycopg2.extensions.POLL_OK:
                if connection.notifies:
                    notify = connection.notifies.pop()
                    # New notify message
                    cur = connection.cursor()
                    query = (
                        "UPDATE bridge_ledger "
                        "SET confirmations = confirmations + 1 "
                        "WHERE txid = %s AND currency = %s"
                    )
                    cur.execute(query, (notify, self.code))
        except (psycopg2.Error, Exception) as e:
            if connection:
                connection.rollback()
                connection.close()
            print "psycopg2 error: " + e.message
        else:
            connection.commit()
            connection.close()


if __name__ == '__main__':
    cr = CoinReactor('NET')
    sys.exit(0)
