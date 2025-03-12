from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


Base = declarative_base()


class Serializer(object):
    def serialize(self):
        return {c: getattr(self, c) for c in inspect(self).attrs.keys()}

    @staticmethod
    def serialize_list(l):
        return [m.serialize() for m in l]


class Favorites(Base, Serializer):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True)
    path = Column(String, nullable=False, unique=True)
    chonky_object = Column(String, nullable=False)
    bucket_source = Column(String, nullable=False)
    bucket_source_type = Column(String, nullable=False)

    def __init__(self, path, chonky_object, bucket_source, bucket_source_type):
        self.path = path
        self.chonky_object = chonky_object
        self.bucket_source = bucket_source
        self.bucket_source_type = bucket_source_type

    def serialize(self):
        d = Serializer.serialize(self)
        return d

    def __repr__(self):
        return f"Favorite(id={self.id!r}, path={self.path!r}, chonky_object={self.chonky_object!r}, bucket_source={self.bucket_source!r}, bucket_source_type={self.bucket_source_type!r})"
    

class Downloads(Base, Serializer):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True)
    pid = Column(Integer, nullable=False, unique=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(String, nullable=False)

    def __init__(self, pid, name, status, message):
        self.pid = pid
        self.name = name
        self.status = status
        self.message = message

    def serialize(self):
        d = Serializer.serialize(self)
        return d

    def __repr__(self):
        return f"Downloads(id={self.id!r}, pid={self.pid!r}, name={self.name!r}, status={self.status!r}, message={self.message!r})"


class DBHandler():
    def __init__(self):
        self.engine = create_engine('sqlite:///.bxplorer.db')
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        insp = inspect(self.engine)
        if not Path('.bxplorer.db').exists() or not insp.has_table("favorites", schema=Favorites.metadata.schema) or not insp.has_table("downloads", schema=Downloads.metadata.schema):
            Favorites.__table__.create(bind=self.engine, checkfirst=True)
            Downloads.__table__.create(bind=self.engine, checkfirst=True)


    def get_session(self):
        insp = inspect(self.engine)
        if not Path('.bxplorer.db').exists() or not insp.has_table("favorites", schema=Favorites.metadata.schema) or not insp.has_table("downloads", schema=Downloads.metadata.schema):
            Favorites.__table__.create(bind=self.engine, checkfirst=True)
            Downloads.__table__.create(bind=self.engine, checkfirst=True)
        
        return self.session
        