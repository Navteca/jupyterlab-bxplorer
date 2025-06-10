"""
Module for managing a download history database using SQLAlchemy.

This script defines a `download_history` table and provides functions to insert,
update, delete, and clean up records related to file downloads. It stores details such as
the S3 bucket name, object key, local file path, download status, error messages,
and start/end timestamps.

Environment Variables:
- DOWNLOAD_HISTORY_DB: Optional. Overrides the default SQLite database URL.

Classes:
- DownloadHistory: SQLAlchemy model representing a single download record.

Functions:
- insert_download_history(bucket, key, local_path): Adds a new record with initial status
  'downloading'.
- update_download_history(record_id, status, error_message=None): Updates status and sets
  end timestamp if applicable.
- clear_download_history(): Deletes all records with a status other than 'downloading'.
- delete_download_history(record_id): Deletes a record if its status is not 'downloading'.
"""

import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuración de la base de datos (asegúrate de ajustar la ruta o conexión según tu entorno)
DATABASE_URL = os.environ.get("DOWNLOAD_HISTORY_DB", "sqlite:///.download_history.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

Base = declarative_base()


class DownloadHistory(Base):
    """
    SQLAlchemy model for storing download history records.

    Each record logs metadata about a file download, including the source
    (bucket and key), destination path, current status, any error messages,
    and timestamps for the start and end of the download.
    """

    __tablename__ = "download_history"
    id = Column(Integer, primary_key=True)
    bucket = Column(String(128), nullable=False)
    key = Column(String(1024), nullable=False)
    local_path = Column(String(1024), nullable=False)
    status = Column(String(64), nullable=False)
    error_message = Column(Text, nullable=True)
    start_time = Column(String(64), nullable=False)
    end_time = Column(String(64), nullable=True)


# Crear la tabla en la base de datos (si aún no existe)
Base.metadata.create_all(engine)


def insert_download_history(bucket, key, local_path):
    """
    Inserta un nuevo registro en el historial de descargas.
    Registra el bucket, key, local_path y establece el estado inicial como 'downloading'.
    Devuelve el id del registro insertado.
    """
    session = Session()
    try:
        download = DownloadHistory(
            bucket=bucket,
            key=key,
            local_path=local_path,
            status="downloading",
            start_time=datetime.datetime.utcnow(),
        )
        session.add(download)
        session.commit()
        return download.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_download_history(record_id, status, error_message=None):
    """
    Actualiza el registro de historial de descarga identificado por record_id.
    Se actualiza el estado, y en caso de finalizar (con éxito o error), se establece 
    el timestamp final.
    Si se proporciona error_message, se almacena para referencia.
    """
    session = Session()
    try:
        download = session.query(DownloadHistory).get(record_id)
        if download:
            download.status = status
            # Si la descarga ha finalizado (success o error), registra el end_time
            if status in ["success", "error"]:
                download.end_time = datetime.datetime.utcnow()
            if error_message:
                download.error_message = error_message
            session.commit()
        else:
            raise ValueError(f"Registro con id {record_id} no encontrado.")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def clear_download_history():
    """
    Elimina todos los registros cuyo estado sea distinto de 'downloading'.
    De esta forma se conservan en el historial únicamente las descargas pendientes.
    """
    session = Session()
    try:
        # Se eliminan registros que hayan finalizado (success o error)
        deleted = (
            session.query(DownloadHistory)
            .filter(DownloadHistory.status != "downloading")
            .delete(synchronize_session=False)
        )
        session.commit()
        return deleted  # se retorna la cantidad de registros borrados (opcional)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_download_history(record_id):
    """
    Elimina un registro del historial identificándolo por record_id,
    siempre y cuando la descarga no se encuentre pendiente (status != 'downloading').
    """
    session = Session()
    try:
        download = session.query(DownloadHistory).get(record_id)
        if not download:
            raise ValueError("Registro no encontrado.")
        if download.status == "downloading":
            raise ValueError("No se puede borrar una descarga pendiente.")
        session.delete(download)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
