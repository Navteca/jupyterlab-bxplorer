import logging
import queue

from urllib3 import connectionpool
from urllib3.exceptions import EmptyPoolError
from urllib3.util.connection import is_connection_dropped

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('nose').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)


# https://github.com/urllib3/urllib3/issues/951
def _get_conn(self, timeout=None):
    conn = None
    try:
        conn = self.pool.get(block=self.block, timeout=timeout)

    except AttributeError:  # self.pool is None
        return self._new_conn()

    except queue.Empty:
        if self.block:
            raise EmptyPoolError(
                self, "Pool reached maximum size and no more connections are allowed.",
            )
        pass

    if conn and is_connection_dropped(conn):
        logger.debug("Resetting dropped connection: %s", self.host)
        conn.close()
        if getattr(conn, "auto_open", 1) == 0:
            conn = None

    return conn or self._new_conn()


def fix_urllib_951():
    connectionpool.HTTPConnectionPool._get_conn = _get_conn  # type: ignore