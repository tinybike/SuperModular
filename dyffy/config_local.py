SECRET_KEY = 'UNIQUE SECRET KEY' 

POSTGRES = {
    "host": "localhost",
    "database": "dyffm",
    "user": "dyffm",
    "password": "dyffm",
    "driver": "psycopg2",
    "port": 5432,
}
SQLALCHEMY_DATABASE_URI = (
    "postgresql+" + POSTGRES["driver"] + "://" +
    POSTGRES["user"] + ":" + POSTGRES["password"] + "@" +
    POSTGRES["host"] + "/" + POSTGRES["database"]
)

FACEBOOK_APP_ID = '807459499283753'
FACEBOOK_APP_SECRET = '3a82b21a79bf8fcea78d29c00555513e'

SOUNDCLOUD_ID = "eca340dd4f199a86ea6f8ded9a92fed3"
SOUNDCLOUD_SECRET = "69dd37151b0671e48d7d4fc31a8598d6"
SOUNDCLOUD_USERNAME = "dyffy"
SOUNDCLOUD_PASSWORD = "Coff33_cultur3"
