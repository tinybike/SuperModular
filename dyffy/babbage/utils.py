import json, datetime
from pprint import pprint
from decimal import Decimal

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def prp(o):
    try:
        print json.dumps(o, indent=3, sort_keys=True, cls=DecimalEncoder)
    except TypeError:
        pprint(o)

def emit(name, data):
    return name, data

def epoch(dt):
    """Convert to epoch time"""
    delta = dt - datetime.datetime.utcfromtimestamp(0)
    return delta.total_seconds()
