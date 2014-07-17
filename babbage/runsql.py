#!/usr/bin/env python
import os, time
import psycopg2, psycopg2.extras
from contextlib import contextmanager
import config

def runsql(filename):
    """Execute commands from a standalone .sql script"""
    filepath = os.path.join(os.path.dirname(__file__), 'sql', filename)
    with open(filepath) as sql, cursor_context() as cur:
        sql_file = sql.read()
        delimiter = ';'
        queries = [q.strip() for q in sql_file.split(delimiter)[:-1]]
        for query in queries:
            try:
                cur.execute(query)
            except psycopg2.ProgrammingError as e:
                print "Command skipped:", e
                print query

@contextmanager
def cursor_context(cursor_factory=False):
    '''Database cursor generator: handles connection, commit, rollback,
    error trapping, and closing connection.  Will propagate exceptions.
    '''
    try:
        conn = None
        conn = psycopg2.connect(host=config.POSTGRES["host"],
                                user=config.POSTGRES["user"],
                                password=config.POSTGRES["password"],
                                database=config.POSTGRES["database"],
                                port=config.POSTGRES["port"])
        if not conn or conn.closed:
            attempt = 1
            while attempt < 5 and (not conn or conn.closed):
                print "Attempt:", attempt
                time.sleep(5)
                attempt += 1
                conn = psycopg2.connect(host=config.POSTGRES["host"],
                                        user=config.POSTGRES["user"],
                                        password=config.POSTGRES["password"],
                                        database=config.POSTGRES["database"],
                                        port=config.POSTGRES["port"])
        if not conn or conn.closed:
            raise Exception("Database connection failed after %d attempts." % attempt)
        if cursor_factory:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = conn.cursor()
        yield cur
    except (psycopg2.Error, Exception) as err:
        if conn:
            conn.rollback()
            conn.close()
        print err.message
        raise
    else:
        conn.commit()
        conn.close()

if __name__ == "__main__":
    runsql("resetdb.sql")
