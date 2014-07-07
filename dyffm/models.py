class User(object):

    def __init__(self, id=None, username=None, email=None, wallet_address=None,
                 encrypted_secret=None, encrypted_iv=None):
        self.id = id
        self.username = username
        self.email = email
        self.wallet_address = wallet_address
        self.encrypted_secret = encrypted_secret
        self.encrypted_iv = encrypted_iv

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)
