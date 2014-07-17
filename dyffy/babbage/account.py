#####################
# Accounts/balances #
#####################

from models import Wallet
import db

def wallet_balance(user_id, currency, session=None):
    """Check the balance of a wallet"""
    if session is None:
        session = db.start_session()
    res = session.query(Wallet).filter(Wallet.user_id==user_id).one()
    if res:
        if currency == "DYF":
            return res.dyf_balance, res
        elif currency == "BTC":
            return res.btc_balance, res
    return None

def debit(user_id, amount, currency, session=None, handle_commit=True):
    """
    Debit coins from a wallet.  Set handle_commit to False if your
    transaction includes a debit in combination with other actions.
    """
    debit_complete = False
    balance, res = wallet_balance(user_id, currency, session=session)
    if balance and amount <= balance:
        new_balance = balance - amount
        if currency == "DYF":
            res.dyf_balance -= amount
        elif currency == "BTC":
            res.btc_balance -= amount
        debit_complete = True
        if handle_commit:
            session.commit()
    if debit_complete:
        return new_balance
    else:
        if handle_commit:
            session.rollback()
        return False
