from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config

def start_session(get_engine=False):
    Base = declarative_base()
    engine = create_engine(config.POSTGRES["urlstring"],
                           isolation_level="SERIALIZABLE",
                           echo=False)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    if get_engine:
        return engine, session
    return session

def init():
    global engine
    global session
    engine, session = start_session(get_engine=True)
