import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .download_history import DownloadHistory
from jupyter_server.base.handlers import APIHandler
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

engine = create_engine(
    "sqlite:///cache.db", echo=False, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
Base.metadata.create_all(bind=engine)


class DownloadHistoryHandler(APIHandler):
    """
    Handler para consultar el histórico de descargas.
    """

    async def get(self):
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
