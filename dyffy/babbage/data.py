import datetime
import random
import numpy as np
import pandas as pd
import soundcloud
from models import SoundCloud, SoundCloudBattle
import db
import config

pd.set_option("display.max_rows", 25)
pd.set_option("display.width", 1000)
pd.options.display.mpl_style = "default"

np.set_printoptions(linewidth=500)

def update(e):
    """Check whether our data is up-to-date"""
    # Check if we have a recent song list (< 10 mins old)
    res = (db.session.query(SoundCloud)
             .order_by(SoundCloud.updated.desc())
             .limit(1)
             .all())
    if res:
        time_elapsed = datetime.datetime.now() - res[0].updated
        if time_elapsed.total_seconds() < 600:
            if config.DEBUG:
                print "SoundCloud data up-to-date."
            return
    update_soundcloud(e)

def update_soundcloud(e):
    """Download data from the SoundCloud API"""
    if config.DEBUG:
        print "Downloading updated track info from SoundCloud..."

    # Create the SoundCloud API client
    client = soundcloud.Client(client_id=config.SOUNDCLOUD["id"],
                               client_secret=config.SOUNDCLOUD["secret"],
                               username=config.SOUNDCLOUD["username"],
                               password=config.SOUNDCLOUD["password"])

    # Get audio track list for selected genre from the SoundCloud API
    tracks = client.get("/tracks",
                        genres=e.genre,
                        types="recording,live,remix,original",
                        limit=config.DATA["soundcloud"]["downloads"])

    # Extract the data into a dataframe
    track_data = [[t.id, t.genre.lower(), t.user_id, t.duration,
                   t.favoritings_count, t.playback_count] for t in tracks]
    df = pd.DataFrame(track_data,
                      columns=["soundcloud_id", "genre", "artist",
                               "duration", "favorites", "playbacks"])
    
    # Calculate song's "mojo" (%) as a sum of normalized
    # favorites and playbacks
    df["updated"] = datetime.datetime.now()
    df["mojo"] = 50*(df.favorites/float(max(df.favorites)) +
                     df.playbacks/float(max(df.playbacks)))
    df = df.sort("mojo", ascending=False)

    # Insert the ranked tracks into the database
    df.to_sql("soundcloud", db.engine, if_exists="append", index=False)
    
    # Select songs at random from the top 25 songs for the "battle",
    # and insert these into the database
    for i in xrange(config.DATA["soundcloud"]["battle-choices"]):
        select = df.ix[random.sample(df.index[:config.DATA["soundcloud"]["top"]], 1)][:1]
        jellybeans = Jellybeans(
            soundcloud_id=select.soundcloud_id.values[0],
            genre=e.genre,
            duration=e.duration
        )
        db.session.add(jellybeans)
    db.session.commit()
