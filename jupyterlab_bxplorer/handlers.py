import boto3
import concurrent.futures
import functools
import importlib.resources as pkg_resources
import json
import logging
import os
import requests
import shlex
import sqlalchemy
import subprocess
import sys
import tornado

from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
from json import dumps
#from mypy_boto3_s3.client import S3Client
from mypy_boto3_s3.paginator import ListObjectsV2Paginator
from mypy_boto3_s3.type_defs import (CommonPrefixTypeDef,
                                     ListObjectsV2OutputTypeDef,
                                     ObjectTypeDef)
from astropy.io import fits
from pathlib import Path
from shutil import which
from typing import Any, Dict, List, Union
from werkzeug.exceptions import BadRequest
from yaml import YAMLError, load

from .db_handler import DBHandler, Favorites, Downloads
from .custom_encoders.JSONEncoder import DTEncoder
from .custom_exceptions.CustomExceptions import ODSourceNotFound, GitHubAPICallRateLimitExceeded, BucketIsNotAccessibleError
from .custom_types.ChonkyFileData import ChonkyFileData
from .custom_types.ChonkyFilesListCache import ChonkyFileListCache
from .custom_types.RequestResponse import RequestResponse
from .FixUrllib951 import fix_urllib_951

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('nose').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

# https://github.com/urllib3/urllib3/issues/951
fix_urllib_951()

buckets_list_data = ChonkyFileListCache()
aws_open_data_bucket_list = ChonkyFileListCache()
ms_open_data_bucket_list = ChonkyFileListCache()
google_open_data_bucket_list = ChonkyFileListCache()
open_data_files_list = ChonkyFileListCache()


od_sources: List[Dict[str, Any]] = [
    {"name": 'AWS', "url": 'https://api.github.com/repos/awslabs/open-data-registry/contents/datasets', "cache": aws_open_data_bucket_list, "disabled": False },
    {"name": 'Microsoft', "url": '', "cache": ms_open_data_bucket_list, "disabled": True },
    {"name": 'Google', "url": '', "cache": google_open_data_bucket_list, "disabled": True }
]


@functools.lru_cache()
def _get_signed_s3_client():
    session = boto3.Session()
    s3 = session.client("s3") # type: ignore
    return s3


@functools.lru_cache()
def _get_unsigned_s3_client():
    s3 = boto3.client('s3', config=Config(max_pool_connections=50, signature_version=UNSIGNED))
    return s3


@functools.lru_cache()
def single_accessible_bucket_check(s3_client, bucket: str) -> Union[str, None]:
    paginator = s3_client.get_paginator('list_objects_v2')
    results: ListObjectsV2Paginator[ListObjectsV2OutputTypeDef]
    try:
        results = paginator.paginate(Bucket=bucket, PaginationConfig={
            'MaxItems': 1,
            'PageSize': 1,
        })
        if results:
            return [result for result in results][0]['Name']
    except ClientError as e:
        return None
    except Exception as e:
        raise Exception(f"Unexpected error: {e}")


class GetChonkyFileDataHandler(APIHandler):
    @tornado.web.authenticated  # type: ignore
    def post(self):
        try:
            s3_data = []
            bucket: str = ''
            prefix: str = ''
            response = {}

            request_data = self.get_json_body()
            if request_data:
                od_source = request_data.get('source', None)
                client_type = request_data.get('clientType', None)
                if od_source:
                    od_sources_information: List[Dict[str, str]] = []
                    od_info = list(filter(lambda e: e['name'] == od_source, od_sources))
                    if od_info:
                        cache = od_info[0]['cache']
                        if not cache.files_list or cache.expires_on <= datetime.now():
                            od_files = requests.get(od_info[0]['url'])
                            if od_files.status_code != 200:
                                raise GitHubAPICallRateLimitExceeded(od_source)
                            open_data_files_list.expires_on = datetime.utcnow() + timedelta(days=1)  # type: ignore

                            od_files_info = [
                                {
                                    "od_bucket_name": os.path.basename(e['download_url']).split('.')[0],
                                    "download_url": e['download_url']
                                }
                                for e in od_files.json()
                            ]

                            with concurrent.futures.ThreadPoolExecutor(30) as executor:
                                futures = {executor.submit(
                                    self.get_od_information_from_file, od_bucket['download_url']): od_bucket for od_bucket in od_files_info}
                                for future in concurrent.futures.as_completed(futures):
                                    data = future.result()
                                    od_sources_information.append(data)

                            od_sources_information[:] = dict((v['name'], v) for v in od_sources_information if v).values()

                            response = [
                                ChonkyFileData(
                                    id=info['name'],
                                    name=info['name'],
                                    isDir=True,
                                    additionalInfo=[{
                                        "openDataHumanName": info['human_name'],
                                        "openDataDescription": info['long_description'],
                                        "region": info['region'],
                                        "type": client_type
                                    }]
                                ).as_dict()
                                for info in od_sources_information if info
                            ]
                            response = sorted(response, key=lambda d: d['name'].lower())
                            cache.files_list = response
                            cache.expires_on = datetime.now() + timedelta(days=1)
                        else:
                            response = cache.files_list
                    else:
                        raise ODSourceNotFound(od_source)
                else:
                        bucket = request_data['bucket']
                        prefix = request_data['prefix']
                        client_type = request_data['clientType']
                        s3_client = _get_signed_s3_client()
                        if client_type == 'public':
                            s3_client = _get_unsigned_s3_client()
                        if bucket == '':
                            if not buckets_list_data.files_list or buckets_list_data.expires_on <= datetime.now():
                                all_buckets = s3_client.list_buckets()

                                with concurrent.futures.ThreadPoolExecutor(len(all_buckets['Buckets'])) as executor:
                                    futures = {executor.submit(
                                        single_accessible_bucket_check, s3_client, bucket['Name']): bucket for bucket in all_buckets['Buckets']}
                                for future in concurrent.futures.as_completed(futures):
                                    data = future.result()
                                    s3_data.append(data)

                                bucket_list = list(
                                    filter(lambda ele: ele is not None, s3_data))
                                response = [ChonkyFileData(
                                    id=bucket,
                                    name=bucket,
                                    isDir=True,
                                    additionalInfo=[{"type": client_type}]).as_dict() for bucket in bucket_list]
                                response = sorted(response, key=lambda d: d['name'].lower())
                                buckets_list_data.files_list = response
                                buckets_list_data.expires_on = datetime.now() + timedelta(days=1)
                            else:
                                response = buckets_list_data.files_list
                        else:
                            new_prefix = prefix[len((bucket + '/')):] if bucket in prefix else prefix
                            chonky_file_structure = self.get_bucket_objects(s3_client, bucket, new_prefix)
                            response = sorted([t.as_dict() for t in chonky_file_structure], key=lambda d: d['name'].lower())

            else:
                raise BadRequest('There has been an error processing the request data. Please, check a bucket and prefix had been provided.')
        except GitHubAPICallRateLimitExceeded as e:
            logger.info(f"{e}")
            self.finish(json.dumps({}))
        except ODSourceNotFound as e:
            logger.info(f"Source {e.od_source} not found.")
        except BadRequest as e:
            print(f"There has been an error processing the request data in {sys._getframe(  ).f_code.co_name} => {e}")
        except ClientError as e:
            logger.info(
                f"Boto3 Client Error while listing object in bucket: {e}")
        except Exception as e:
            logger.info(f"There has been an unexpected error in GetChonkyFileDataHandler")
        else:
            self.finish(json.dumps(response, cls=DTEncoder))


    def get_bucket_objects(self, s3_client, bucket: str, prefix: str) -> List[ChonkyFileData]:
        chonkyFiles: List[ChonkyFileData] = []
        try:
            bucket_objects: ListObjectsV2OutputTypeDef = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix if prefix != '/' else '', Delimiter='/')
            s3_objects: Union[List[ObjectTypeDef], None] = bucket_objects.get('Contents', None)
            s3_prefixes: Union[List[CommonPrefixTypeDef], None] = bucket_objects.get('CommonPrefixes', None)
            if s3_objects:
                chonkyFiles += [
                    ChonkyFileData(
                        id=obj.get('Key', ''),
                        name=os.path.basename(obj.get('Key', '')),
                        modDate=obj.get('LastModified', ''),
                        size=obj.get('Size'),
                        additionalInfo=[{"region": bucket_objects.get('ResponseMetadata', {}).get('HTTPHeaders', {}).get('x-amz-bucket-region', '')}]
                    )
                    for obj in s3_objects
                ]

            if s3_prefixes:
                chonkyFiles += [
                    ChonkyFileData(
                        id=obj.get('Prefix', ''),
                        name=os.path.basename(obj.get('Prefix', '').strip('/')),
                        isDir=True,
                        additionalInfo=[{"region": bucket_objects.get('ResponseMetadata', {}).get('HTTPHeaders', {}).get('x-amz-bucket-region', '')}]
                    )
                    for obj in s3_prefixes
                ]
        except ClientError as e:
            logger.info(f"Generic exception => {e.response}")
            if e.response.get('Error', {}).get('Code', None) == 'NoSuchBucket':
                print(f"{e.response.get('Error', {}).get('Message', 'No Message')}: {e.response.get('Error', {}).get('BucketName', 'No bucket name')}")
            else:
                logger.info(f"Other S3 ClientError => {e.response}")
        return chonkyFiles


    def get_od_information_from_file(self, od_file_url: str) -> Dict[str, Any]:
        od_file_info = {}
        try:
            info = requests.get(od_file_url)
            yaml_info = load(info.text, SafeLoader)
            if yaml_info['Resources'][0]['Type'] == 'S3 Bucket':
                od_file_info = {
                    "name": yaml_info['Resources'][0]['ARN'].split(':')[-1:][0],
                    "human_name": yaml_info['Name'],
                    "long_description": yaml_info['Description'],
                    "region": yaml_info['Resources'][0]['Region']
                }
        except requests.exceptions.RequestException as e:
            raise Exception(
                f"There has been an error getting info for {os.path.basename(od_file_url)} =< {e}")
        except YAMLError as e:
            logger.info(f"Error in YAML => {e}")
            raise Exception(f"Error in YAML => {e}")
        else:
            return od_file_info


class GetOpenDataSourcesListHandler(APIHandler):
    @tornado.web.authenticated  # type: ignore
    def get(self):
        self.finish({"sources": list(map(lambda e: e['name'], od_sources))})


class DownloadsHandler(APIHandler):
    db = DBHandler()


    def get_buckets_files_folders(self, s3_client, bucket_name, prefix=""):
        try:
            file_names = []
            folders = []

            default_kwargs = {
                "Bucket": bucket_name,
                "Prefix": prefix
            }

            next_token = ""

            while next_token is not None:
                updated_kwargs = default_kwargs.copy()
                if next_token != "":
                    updated_kwargs["ContinuationToken"] = next_token

                response = s3_client.list_objects_v2(**default_kwargs)
                contents = response.get("Contents")

                for result in contents:
                    key = result.get("Key")
                    if key[-1] == "/":
                        folders.append(key)
                    else:
                        file_names.append(key)

                next_token = response.get("NextContinuationToken")
        except Exception as e:
            logger.info(f"Something went wrong getting the list of files => {e}")
            return None, None
        else:
            return file_names, folders


    def getDownloads(self):
        downloads_list = []
        with self.db.get_session() as session:
            for download in session.query(Downloads).all():
                downloads_list.append(download.serialize())
        return downloads_list


    @tornado.web.authenticated  # type: ignore
    def post(self):
        response: RequestResponse = RequestResponse()
        try:
            bucket: str = ''
            prefix: str = ''
            source: str = ''
            request_data = self.get_json_body()
            if request_data:
                bucket = request_data['bucket']
                prefix = request_data['prefix']
                source = request_data['source']
                downloadPath = request_data['downloadPath']
                s3_uri = f"{bucket}/{prefix}"

                if not Path(downloadPath).exists():
                    Path.mkdir(Path(downloadPath), parents=True, exist_ok=True)
                client_type = 'unsigned' if source.lower() in ['aws', 'google', 'microsoft'] else 'signed'
                if s3_uri and downloadPath:
                    with pkg_resources.path('jupyterlab_bxplorer', 'cmd_launcher.py') as p:
                        cmd_split = shlex.split(f"{which('python')} {p} {s3_uri} {downloadPath} {client_type}")
                        subprocess.Popen(cmd_split, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                response.status_code = 200
                response.data = f"Your files have been downloaded successfully."
            else:
                response.status_code = 620
                response.data = f"THe required data has not been received. Please send bucket, prefix, source."
        except FileNotFoundError as e:
            logger.info(f'There has been an error creating folder structure => {e}')
            response.status_code = 621
            response.data = f"THere has been a problem creating the folder structure, please contact the administrator."
        except Exception as e:
            logger.info(f"It was not possible to download the selected files, please contact the administrator.")
            response.status_code = 622
            response.data = f"It was not possible to download the selected files, please contact the administrator."
        else:
            self.finish(response.as_dict())


    @tornado.web.authenticated  # type: ignore
    def get(self):
        try:
            downloads = self.getDownloads()
            self.finish(json.dumps(downloads))
        except Exception as e:
            logger.info(f"There has been an exception reading the bxplorer db => {e}")
    

    @tornado.web.authenticated  # type: ignore
    def delete(self):
        response: RequestResponse = RequestResponse()
        try:
            request_data = self.get_json_body()
            if request_data:
                delete_all = request_data['deleteAll']
                if delete_all:
                    with self.db.get_session() as session:
                        session.query(Downloads).delete()
                        session.commit()
                        response.status_code = 200
                        response.data = f"All Deleted."
                else:
                    id_to_del = request_data['id']
                    pid_to_del = request_data['pid']
                    with self.db.get_session() as session:
                        download_to_delete = session.query(Downloads).filter(Downloads.id == id_to_del, Downloads.pid == pid_to_del).first()
                        if download_to_delete:
                            session.delete(download_to_delete)
                            session.commit()
                            response.status_code = 200
                            response.data = f"Delete."
                        else:
                            response.status_code = 700
                            response.data = f"Not Deleted"
            else:
                response.status_code = 701
                response.data = f"There has been an error with the data sent to the backend. Please check with your administrator"
        except sqlalchemy.exc.IntegrityError as e:   # type: ignore
            logger.info(f'Integrity Check failed => {e}')
            self.finish(json.dumps([]))  
        except Exception as e:
            logger.info(f"There has been an error deleting downloaded => {e}")
        else:
            self.finish(json.dumps(response.as_dict()))


class FavoritesHandler(APIHandler):
    db = DBHandler()


    def getAllFavorites(self):
        chonky_favorites = []
        with self.db.get_session() as session:
            for favorite in session.query(Favorites).all():
                chonky_favorites.append(favorite.serialize())
        return chonky_favorites


    @tornado.web.authenticated  # type: ignore
    def get(self):
        try:
            chonky_favorites = self.getAllFavorites()
            self.finish(json.dumps(chonky_favorites))
        except Exception as e:
            logger.info(f"There has been an exception reading the favorites db => {e}")

    
    @tornado.web.authenticated  # type: ignore
    def post(self):
        response: RequestResponse = RequestResponse()
        try:
            request_data = self.get_json_body()
            if request_data:
                path = request_data['path']
                chonky_object = request_data['chonky_object']
                bucket_source = request_data['bucket_source']
                bucket_source_type = request_data['bucket_source_type']
                s3_client = _get_unsigned_s3_client() if bucket_source_type.lower() in ['public', 'external'] else _get_signed_s3_client()

                accessible = single_accessible_bucket_check(s3_client, path)
                if not accessible:
                    response.status_code = 602
                    response.error.code = 602
                    response.error.message = f"The bucket {path} is not accessible."
                    raise BucketIsNotAccessibleError(path)
                new_obj = Favorites(path, dumps(chonky_object), bucket_source, bucket_source_type)
                with self.db.get_session() as session:
                    bucketFound = session.query(Favorites.path).filter_by(path=path).first()
                    if bucketFound:
                        response.status_code = 600
                        response.error.code = 600
                        response.error.message = f"The bucket {path} already exists in your favorites list."
                    else:
                        session.add(new_obj)
                        session.commit()
                        response.status_code = 200
                        response.data = f"The bucket {path} has been added to your favorites list."
            else:
                response.status_code = 603
                response.error.code = 603
                response.error.message = "Request Data is not correct."
        except sqlalchemy.exc.IntegrityError as e:   # type: ignore
            logger.info(f'Integrity Check failed => {e}')
            response.status_code = 601
            response.error.code = 601
            response.error.message = f"Integrity check error {e}"
        except BucketIsNotAccessibleError as e:
            logger.info(f"{e}")
        finally:
            self.finish(response.as_dict())


    @tornado.web.authenticated  # type: ignore
    def delete(self):
        response: RequestResponse = RequestResponse()
        try:
            request_data = self.get_json_body()
            if request_data:
                with self.db.get_session() as session:
                    favorite_to_delete = session.query(Favorites).where(Favorites.path == request_data).first()
                    if favorite_to_delete:
                        session.delete(favorite_to_delete)
                        session.commit()
                        response.status_code = 200
                        response.data = f"The bucket {request_data} has been deleted from your favorites list."
                    else:
                        response.status_code = 604
                        response.data = f"The bucket {request_data} has not been found in your favorites list."
            else:
                response.status_code = 605
                response.data = f"There has been an error with the data sent to the backend. Please check with your administrator"
                # chonky_favorites = self.getAllFavorites()
        except sqlalchemy.exc.IntegrityError as e:   # type: ignore
            logger.info(f'Integrity Check failed => {e}')
            self.finish(json.dumps([]))  
        except Exception as e:
            logger.info(f"There has been an error deleting favorite => {e}")
        else:
            logger.info(f"Deleting Response => {response.as_dict()}")
            self.finish(response.as_dict())


class FitsHandler(APIHandler):
    @tornado.web.authenticated  # type: ignore
    def get(self):
        try:            
            request_data = self.request.arguments
            self.log.info(request_data)
            if request_data:
                fits_file = request_data['file']
                bucket = request_data['bucket']
                anonymous = request_data['anon']
            
            file_name = str(fits_file[0], 'utf-8')
            bucket_name = str(bucket[0], 'utf-8')
            anon = str(anonymous[0], 'utf-8') == 'true'

            fsspec_kwargs = {"anon": anon}
            uri = f"s3://{bucket_name}/{file_name}"
            # uri = "s3://nasa-irsa/spitzer/seip/seip_science/images/2/0000/20000011/0/20000011-0/20000011.20000011-0.MIPS.1.cov.fits"
            with fits.open(uri, use_fsspec=True, fsspec_kwargs=fsspec_kwargs, memmap=True) as hdul:
                header = hdul[0].header
                info = {}
                for key in header:
                    if not isinstance(header[key], fits.header._HeaderCommentaryCards):
                        info.update({key: str(header[key + '*'])})

            self.finish(json.dumps(info))
        except Exception as e:
            self.log.info(f"There has been an exception reading the favorites db => {e}")

def setup_handlers(web_app):
    host_pattern = ".*$"

    base_path = url_path_join(web_app.settings["base_url"], "jupyterlab-bxplorer")
    handlers = [
        (url_path_join(base_path, "get_file_data"), GetChonkyFileDataHandler),
        (url_path_join(base_path, "/open_data/get_sources_list"), GetOpenDataSourcesListHandler),
        (url_path_join(base_path, "downloads"), DownloadsHandler),
        (url_path_join(base_path, "favorites"), FavoritesHandler),
        (url_path_join(base_path, "fits"), FitsHandler)
    ]
    web_app.add_handlers(host_pattern, handlers)
