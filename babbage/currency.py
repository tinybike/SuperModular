############
# Currency #
############

from decimal import Decimal

def get_precision(currency_code):
    if currency_code == 'NXT':
        precision = '.01'
    elif currency_code == 'XRP':
        precision = '.000001'
    else:
        precision = '.00000001'
    return Decimal(precision)
