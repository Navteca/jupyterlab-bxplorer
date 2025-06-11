"""
Module providing an HTTP API handler for interacting with the download history database.

This module defines a Jupyter server extension handler that exposes endpoints to:
- Retrieve all download history records.
- Delete individual records by ID.
- Clean up completed or failed downloads.

It uses SQLAlchemy for database interaction and expects the download history model and utility
functions to be imported from `download_history.py`.

Classes:
- DownloadHistoryHandler: Handles GET and DELETE requests related to download history records.

Dependencies:
- SQLAlchemy: For database operations.
- Jupyter Server: Provides the APIHandler base class.
"""

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jupyter_server.base.handlers import APIHandler
from .download_history import (
    DownloadHistory,
    Base,
    clear_download_history,
    delete_download_history,
    DATABASE_URL,
)

engine = create_engine(
    DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
Base.metadata.create_all(bind=engine)


class DownloadHistoryHandler(APIHandler):
    """
    Jupyter API handler for managing download history records.

    Supports:
    - GET: Returns a JSON list of all download records, ordered by start time (descending).
    - DELETE:
        * With `?action=clean`: Deletes all records not currently downloading.
        * With `?id=<record_id>`: Deletes a specific record by ID, unless it's still downloading.
    """

    def data_received(self, chunk):
        """
        Override required by the base class RequestHandler.
        This method is not used in this handler, as the handler does not process streaming data.
        """

    async def get(self):
        """
        Handles GET requests for retrieving download history records.

        Queries the database for all download history records, ordered by start time
        in descending order. Returns a JSON response with the records, including details
        such as bucket, key, local path, status, start time, end time, and error messages.

        If an error occurs during the process, a 500 status code with the error message is returned.
        """
        try:
            # Se consultan todos los registros ordenados por fecha de inicio descendente
            records = (
                session.query(DownloadHistory)
                .order_by(DownloadHistory.start_time.desc())
                .all()
            )
            downloads = []
            for record in records:
                downloads.append(
                    {
                        "id": record.id,
                        "bucket": record.bucket,
                        "key": record.key,
                        "local_path": record.local_path,
                        "start_time": record.start_time,
                        "end_time": record.end_time,
                        "status": record.status,
                        "error_message": record.error_message,
                    }
                )
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(downloads))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))

    async def delete(self):
        """
        Maneja la eliminación de registros del historial:
        - Si se pasa ?action=clean, se borran todas las descargas que no estén pendientes.
        - Si se pasa ?id=<record_id>, se intenta eliminar ese registro individual,
          validando que no se trate de una descarga pendiente.
        """
        action = self.get_argument("action", None)
        try:
            if action == "clean":
                # Limpiar historial: eliminar descargas completadas o con error.
                deleted_count = clear_download_history()
                self.write(
                    json.dumps(
                        {
                            "status": "success",
                            "message": f"Historial limpiado. Registros eliminados: {deleted_count}.",
                        }
                    )
                )
            else:
                record_id = self.get_argument("id", None)
                if not record_id:
                    self.set_status(400)
                    self.write(
                        json.dumps({"error": "Debe proporcionar un id o action=clean."})
                    )
                    return
                try:
                    record_id_int = int(record_id)
                except ValueError:
                    self.set_status(400)
                    self.write(
                        json.dumps({"error": "El id debe ser un número entero."})
                    )
                    return
                delete_download_history(record_id_int)
                self.write(
                    json.dumps(
                        {
                            "status": "success",
                            "message": f"Registro {record_id_int} eliminado.",
                        }
                    )
                )
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))
