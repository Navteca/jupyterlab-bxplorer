import os
from sqlalchemy import create_engine, Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración de la base de datos (asegúrate de ajustar la ruta o conexión según tu entorno)
DATABASE_URL = os.environ.get("FAVORITES_DB", "sqlite:///.favorites.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

Base = declarative_base()

# Crear la tabla en la base de datos (si aún no existe)
Base.metadata.create_all(engine)


class Favorite(Base):
    __tablename__ = "favorites"

    bucket = Column(String, primary_key=True)
    is_private = Column(Boolean, nullable=False)


def add_favorite(bucket: str, is_private: bool):
    session = Session()
    try:
        fav = Favorite(bucket=bucket, is_private=is_private)
        session.merge(fav)
        session.commit()
    finally:
        session.close()


def remove_favorite(bucket: str):
    session = Session()
    try:
        session.query(Favorite).filter(Favorite.bucket == bucket).delete()
        session.commit()
    finally:
        session.close()


def list_favorites() -> list[dict]:
    session = Session()
    try:
        favorites = session.query(Favorite).all()
        return [
            {
                "name": fav.bucket,
                "isFile": False,
                "path": f"/{fav.bucket}/",
                "hasChild": True,
                "type": "folder",
                "size": "-",
                "dateModified": "-",
                "region": "-" if not fav.is_private else "private",
            }
            for fav in favorites
        ]
    finally:
        session.close()
