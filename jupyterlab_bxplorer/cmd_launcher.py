import subprocess
import shlex
import logging
import os
import boto3
import math
import psutil
import functools

from shutil import which
from pathlib import Path
from botocore import exceptions
from argparse import ArgumentParser
from db_handler import Downloads, DBHandler
from botocore import UNSIGNED
from botocore.config import Config
from typing import Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@functools.lru_cache()
def _get_signed_s3_client():
    session = boto3.Session()
    s3 = session.resource("s3")
    return s3


@functools.lru_cache()
def _get_unsigned_s3_client():
    s3 = boto3.resource('s3', config=Config(max_pool_connections=50, signature_version=UNSIGNED))
    return s3


class Error(Exception):
    pass


class NotEnoughSpaceOnDevice(Error):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return f"There is not enough space left on the device."

    
class LargeFileWarning(Error):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return f"The file you are trying to download is large and this might affect JupyterLab functioning."

    
class ApplicationNotFound(Error):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return f"The specified application has not been found."


def get_size(bucket: str, path: str, client):
    my_bucket = client.Bucket(bucket)
    total_size = 0

    for obj in my_bucket.objects.filter(Prefix=path):
        total_size = total_size + obj.size

    return total_size


if __name__ == '__main__':
    parser = ArgumentParser()
    db = DBHandler()
    parser.add_argument("s3_uri", type=str)
    parser.add_argument("path", type=str)
    parser.add_argument("client_type", type=str)
    args = parser.parse_args()
    process = None
    bucket = None
    key = None
    success = None
    total_object_size = 0
    message = ''
    dest = Path('.')

    s3_client = _get_unsigned_s3_client() if args.client_type.lower().strip() == 'unsigned' else _get_signed_s3_client()
    try:
        if which('aws') is None:
            raise ApplicationNotFound()
        
        bucket = Path(args.s3_uri).parts[0]
        key = args.s3_uri.replace(bucket+'/', '')
        filename = os.path.basename(args.s3_uri)
        disk_space_left = psutil.disk_usage(str(Path(args.path).parent))[2]
        object_size = get_size(bucket, key, s3_client)
        total_object_size = round(object_size * 1.10)

        logger.info(f"=====> File Size => {object_size}")

        if object_size > 1000000000:
            raise LargeFileWarning()

        if disk_space_left - total_object_size >= 0:
            if filename == '':
                dest = Path(args.path) / Path(args.s3_uri).parts[-1]
                if not dest.exists():
                    dest.mkdir(parents=True, exist_ok=True)
            else:
                dest = Path(args.path) / filename
            
            cmd_split = shlex.split(f"aws s3 cp {'--recursive' if filename == '' else ''} s3://{args.s3_uri} {dest} {'--no-sign-request' if args.client_type.lower().strip() == 'unsigned' else ''}")
            process = subprocess.Popen(cmd_split, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            success = True
        else:
            raise NotEnoughSpaceOnDevice()
    except exceptions.ClientError as error:
        if error.response.get('Error', {}).get('Code', None) == 'NoSuchKey':
            print(f"The specified Bucket: {key} has not been found")
            message = f"The specified Bucket: {key} has not been found"
        elif error.response.get('Error', {}).get('Code', None) == 'NoSuchBucket':
            print(f"The specified Bucket: {bucket} has not been found")
            message = f"The specified Bucket: {bucket} has not been found"
        else:
            print(f"There has been an error with the S3 client => {error}")
            message = f"There has been an error with the S3 client => {error}"
    except subprocess.CalledProcessError as exc:
        print(f"Program failed {exc.returncode} - {exc}")
        message = f"Program failed {exc.returncode} - {exc}"
    except subprocess.TimeoutExpired as exc:
        print(f"Program timed out {exc}")
        message = f"Program timed out {exc}"
    except NotEnoughSpaceOnDevice as exc:
        print(f"{exc}")
        message = f"{exc}"
    except ApplicationNotFound as exc:
        print(f"{exc}")
        message = f"{exc}"
    except Exception as exc:
        print(f"Exception {exc}")
        message = f"Exception {exc}"
    else:
        success = True
    finally:
        with db.get_session() as session:
            if process:
                newProcess = Downloads(pid=process.pid, name=dest.name, status='', message='')
                newProcess.status = 'Downloading' if success else 'Error'
                newProcess.message = '' if success else message
                session.add(newProcess)
                session.commit()
                              
                out, error = process.communicate()

                if error.strip() != '':
                    session.query(Downloads).filter_by(pid=process.pid).update({'status': 'Error', 'message': error.strip()})

                if out.strip() != '':
                    session.query(Downloads).filter_by(pid=process.pid).update({'status': 'Downloaded'})

                session.commit()
            else:
                print(f"It has not been possible to execute the command. It must be related to the OS")

