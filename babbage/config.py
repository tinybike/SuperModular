import os, platform

if platform.node() in ("vent", "nerve", "heavy"):
    DEPLOY_ENV = "development"
    DEBUG = True
else:
    DEPLOY_ENV = "production"

TESTING = False

# betting engine postgres connection
POSTGRES = {
    "host": "localhost",
    "database": "babbage",
    "user": "babbage",
    "password": "Coff33_cultur3",
    "driver": "psycopg2",
    "port": 5432,
}
POSTGRES["urlstring"] = (
    "postgresql+" + POSTGRES["driver"] + "://" +
    POSTGRES["user"] + ":" + POSTGRES["password"] + "@" +
    POSTGRES["host"] + "/" + POSTGRES["database"]
)

# threshold for betting markets to close unchanged/neutral
NEUTRAL_THRESHOLD = 1e-07

# tables storing users" bets for the current round
BET_TABLES = ["bets",]
BET_HISTORY_TABLES = ["bet_history",]

# Coin daemon info
COINS = {
    "bitcoin": {
        "ticker": "BTC",
        "confirmations": 6,
        "network-port": "8333",
        "network-port-testnet": "18333",
        "rpc-url": "http://127.0.0.1",
        "rpc-port": "8332",
        "rpc-port-testnet": "18332",
        "rpc-user": "ZTwijIDcaRCY",
        "rpc-password": "qBrbIrxGlUhh797oIOwKRN7XN7lavBAq",
        "passphrase": "uMrTVAOVSuoOkqEPcgtyFdiWWzlZOYX5",
        "unlock-timeout": 30,
    }
}
COINS["bitcoin"]["rpc-urlstring"] = "http://ZTwijIDcaRCY:qBrbIrxGlUhh797oIOwKRN7XN7lavBAq@127.0.0.1:8332"

# soundcloud API info
SOUNDCLOUD = {
    "id": "eca340dd4f199a86ea6f8ded9a92fed3",
    "secret": "69dd37151b0671e48d7d4fc31a8598d6",
    "username": "dyffy",
    "password": "Coff33_cultur3",
}

DATA = {
    "soundcloud": {
        "downloads": 100,
        "battle-choices": 10,
        "top": 25,
    }
}
