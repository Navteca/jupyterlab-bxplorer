"""
File Manager Handler for JupyterLab Bxplorer v2 Extension.

This module provides an API handler that allows for interaction with S3 buckets
(both public and private), enabling the following actions:
- Read: List buckets or bucket contents.
- Download: Download files from buckets.
- Details: Retrieve details of specific files or folders.
- Search: Search for items in the root or within a bucket.

The module includes caching using SQLite to improve performance.
"""

import os
import json
import asyncio
import yaml
from datetime import datetime

import tornado.web
import tornado.ioloop
import tornado.httpclient

import boto3
from botocore.exceptions import ClientError
from botocore import UNSIGNED
from botocore.config import Config

import time
from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from jupyter_server.base.handlers import APIHandler

Base = declarative_base()


class Cache(Base):
    """
    Cache class for storing data temporarily in an SQLite database.

    Attributes:
        cache_key (str): Unique key for identifying the cached data.
        value (str): Serialized JSON data stored as text.
        timestamp (float): Timestamp when the data was cached.
    """

    __tablename__ = "cache_table"
    cache_key = Column(String, primary_key=True)
    value = Column(Text)
    timestamp = Column(Float)


engine = create_engine(
    "sqlite:///cache.db", echo=False, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
Base.metadata.create_all(bind=engine)

_CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
PUBLIC_BUCKETS_URL = os.getenv(
    "PUBLIC_BUCKETS_URL",
    "https://api.github.com/repos/awslabs/open-data-registry/contents/datasets",
)
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "tmp")


def _set_cache(key, value):
    """
    Stores a value in the cache.

    Args:
        key (str): The cache key to store the data.
        value (dict): The value to store, serialized to JSON.
    """
    try:
        serialized_value = json.dumps(value)  # Serializamos el dict a JSON
        timestamp = time.time()
        # Buscamos si ya existe un registro con la misma key
        cache_entry = session.query(Cache).filter_by(cache_key=key).first()
        if cache_entry:
            cache_entry.value = serialized_value
            cache_entry.timestamp = timestamp
        else:
            cache_entry = Cache(
                cache_key=key, value=serialized_value, timestamp=timestamp
            )
            session.add(cache_entry)
        session.commit()
    except Exception as e:
        print("Error saving to cache:", e)
        session.rollback()


def _get_from_cache(key):
    """
    Retrieves a value from the cache.

    Args:
        key (str): The cache key to retrieve the data.

    Returns:
        dict or None: The cached data as a dictionary if found and not expired, otherwise None.
    """
    try:
        cache_entry = session.query(Cache).filter_by(cache_key=key).first()
        if cache_entry:
            if time.time() - cache_entry.timestamp < _CACHE_TTL:
                return json.loads(cache_entry.value)  # Deserializamos el JSON a dict
        return None
    except Exception as e:
        print("Error retrieving from cache:", e)
        return None


def get_s3_client(client_type="private"):
    """
    Returns an S3 client with the appropriate configuration.

    Args:
        client_type (str): Type of client ('private' or 'public').

    Returns:
        botocore.client.S3: Configured S3 client.
    """
    if client_type == "public":
        return boto3.client("s3", config=Config(signature_version=UNSIGNED))
    else:
        # session = boto3.Session()
        # return session.client("s3")
        return boto3.client("s3")


def format_size(bytes):
    """
    Converts byte size to a human-readable format (KB, MB, GB).

    Args:
        bytes (int): Size in bytes.

    Returns:
        str: Human-readable string representation of the size.
    """
    for unidad in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unidad}"
        bytes /= 1024.0


def format_item(
    name, is_file, path, has_child, item_type, size=0, date_modified="", region=""
):
    """
    Formats an item (file or folder) to match the expected format of FileManager.

    Args:
        name (str): Name of the item.
        is_file (bool): Whether the item is a file.
        path (str): Path to the item.
        has_child (bool): Whether the item has children.
        item_type (str): Type of the item ('file' or 'folder').
        size (int, optional): Size of the item in bytes.
        date_modified (str, optional): Date the item was last modified.
        region (str, optional): S3 region of the item.

    Returns:
        dict: Formatted item dictionary.
    """
    return {
        "name": name,
        "isFile": is_file,
        "path": path,
        "hasChild": has_child,
        "type": item_type,
        "size": format_size(size) if size != "-" and size != "" else size,
        "dateModified": (
            datetime.fromisoformat(date_modified).strftime("%b %d, %Y")
            if date_modified != "-" and date_modified != ""
            else date_modified
        ),
        "region": region,
    }


def list_bucket_contents(s3_client, bucket_name, prefix):
    """
    Lists the contents of a given bucket and prefix.

    Args:
        s3_client (botocore.client.S3): The S3 client.
        bucket_name (str): Name of the bucket.
        prefix (str): Prefix to list the contents from.

    Returns:
        list: Combined list of files and folders.
    """
    all_files = []
    all_folders = []
    continuation_token = None
    while True:
        # Obtener la región del bucket
        location = s3_client.get_bucket_location(Bucket=bucket_name)[
            "LocationConstraint"
        ]
        region = location if location else "us-east-1"

        list_params = {"Bucket": bucket_name, "Prefix": prefix, "Delimiter": "/"}
        if continuation_token:
            list_params["ContinuationToken"] = continuation_token

        response = s3_client.list_objects_v2(**list_params)

        # Procesar archivos (omitimos el objeto que define la carpeta)
        for obj in response.get("Contents", []):
            key = obj.get("Key", "")
            if key == prefix:
                continue
            file_name = key.split("/")[-1]
            size = obj.get("Size", 0)
            last_modified = obj.get("LastModified")
            date_modified = last_modified.isoformat() if last_modified else ""
            all_files.append(
                format_item(
                    file_name,
                    True,
                    f"/{bucket_name}/{key}",
                    False,
                    "file",
                    size,
                    date_modified,
                    region=region,
                )
            )

        # Procesar carpetas
        for common_prefix in response.get("CommonPrefixes", []):
            folder_prefix = common_prefix.get("Prefix", "")
            folder_name = folder_prefix.rstrip("/").split("/")[-1]
            all_folders.append(
                format_item(
                    folder_name,
                    False,
                    f"/{bucket_name}/{folder_prefix}",
                    True,
                    "folder",
                    size="-",
                    date_modified="-",
                    region=region,
                )
            )

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    return all_folders + all_files


# class BaseHandler(APIHandler):
#     """
#     Base handler for managing API requests with default headers.

#     Methods:
#         set_default_headers: Sets CORS and allowed methods headers.
#         options: Handles OPTIONS requests.
#     """

#     def set_default_headers(self):
#         """
#         Sets the default headers for CORS (Cross-Origin Resource Sharing) and allowed HTTP methods.

#         This method configures the response to allow requests from any origin,
#         specifies the headers that can be included in the request, and defines
#         the HTTP methods that are permitted.

#         Methods:
#             GET, POST, PUT, DELETE, OPTIONS
#         """
#         # Allow any domain to access your API
#         self.set_header("Access-Control-Allow-Origin", "*")
#         # List the allowed headers
#         self.set_header(
#             "Access-Control-Allow-Headers",
#             "x-requested-with, content-type, Authorization",
#         )
#         # List the allowed methods
#         self.set_header(
#             "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
#         )

#     # Handle OPTIONS requests
#     def options(self, *args, **kwargs):
#         """
#         Handles OPTIONS requests.

#         This method sets the status to 204 (No Content) to indicate that the
#         preflight request is successful and terminates the request.
#         """
#         # no body is sent for an OPTIONS request
#         self.set_status(204)
#         self.finish()


class FileManagerHandler(APIHandler):
    """
    Unified handler for FileManager operations (read, download, details, search).

    Methods:
        post: Handles incoming POST requests and performs the appropriate action.
        _list_private_buckets: Lists private buckets.
        _list_public_buckets: Lists public buckets from a JSON file.
        _list_bucket_contents: Lists bucket contents for a given path.
        _download_file: Downloads a file from S3 and saves it locally.
        _get_details: Retrieves details about a file or folder.
        _search_items: Searches for items within buckets or at the root level.
    """

    @tornado.web.authenticated
    async def post(self):
        try:
            content_type = self.request.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = json.loads(self.request.body.decode("utf-8"))
            else:
                download_input_raw = self.get_argument("downloadInput", None)
                if download_input_raw is None:
                    data = json.loads(self.request.body.decode("utf-8"))
                else:
                    data = json.loads(download_input_raw)

        except Exception as e:
            self.set_status(400)
            self.write({"error": "Error parsing JSON:" + str(e)})
            return

        print(f"Received data: {data}")
        action = data.get("action", "").lower()
        print(f"Requested action: {action}")
        path = data.get("path", "").strip()
        client_type = data.get("client_type", "public").lower()
        s3_client = get_s3_client(client_type)

        if action == "read":
            if not path or path == "/":
                if client_type == "private":
                    result = self._list_private_buckets(s3_client)
                else:
                    result = await self._list_public_buckets()
                self.set_header("Content-Type", "application/json")
                self.write(result)
            else:
                result = self._list_bucket_contents(s3_client, path, client_type)
                self.set_header("Content-Type", "application/json")
                self.write(result)
        elif action == "download":
            self._download_file(data, s3_client)
        elif action == "details":
            self._get_details(data, s3_client)
        elif action == "search":
            result = await self._search_items(data, s3_client, client_type)
            self.set_header("Content-Type", "application/json")
            self.write(result)
        else:
            self.set_status(400)
            self.write({"error": "Unsupported action"})

    def _list_private_buckets(self, s3_client):
        """
        Lists private buckets using the `list_buckets` API.

        This method queries private S3 buckets that the user has access to and formats
        the response for use with the FileManager.

        Args:
            s3_client (botocore.client.S3): The authenticated S3 client.

        Returns:
            str: JSON-encoded list of accessible private buckets.
        """
        try:
            cache_key = "private_buckets"
            cached_result = _get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

        except Exception as e:
            self.application.settings.get("logger", print)(
                f"Error accessing cache: {e}"
            )

        try:
            response = s3_client.list_buckets()
            accessible_buckets = []

            for bucket in response.get("Buckets", []):
                name = bucket.get("Name")
                try:
                    location = s3_client.get_bucket_location(Bucket=name)[
                        "LocationConstraint"
                    ]
                    region = location if location else "us-east-1"

                    accessible_buckets.append(
                        format_item(
                            name,
                            False,
                            f"/{name}/",
                            True,
                            "folder",
                            size="-",
                            date_modified="-",
                            region=region,
                        )
                    )
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]
                    if error_code in ["AccessDenied", "AllAccessDisabled"]:
                        continue
                    else:
                        raise

            cwd = format_item("Root", False, "/", True, "folder")
            result = {"cwd": cwd, "files": accessible_buckets}
            try:
                _set_cache(cache_key, result)
            except Exception as e:
                print(f"Error saving to cache: {e}")
            finally:
                session.close()

            return json.dumps(result)
        except ClientError:
            self.set_status(403)
            return json.dumps(
                {"error": "You do not have permission to access private buckets."}
            )
        except Exception as e:
            self.set_status(500)
            return json.dumps({"error": str(e)})

    async def _list_public_buckets(self):
        """
        Retrieves the list of public buckets from a JSON file (downloaded and cached).

        This method downloads a YAML file that contains metadata about public buckets
        and extracts bucket details, formatting them for FileManager.

        Returns:
            dict: A dictionary containing public bucket details.
        """
        try:
            cache_key = "public_buckets"
            cached_result = _get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

        except Exception as e:
            self.application.settings.get("logger", print)(
                f"Error accessing cache: {e}"
            )

        http_client = tornado.httpclient.AsyncHTTPClient()
        datasets_url = PUBLIC_BUCKETS_URL

        try:
            response = await http_client.fetch(datasets_url)
            datasets = json.loads(response.body.decode())
        except Exception as e:
            self.set_status(500)
            self.write({"error": f"Error fetching the list of datasets: {e}"})
            return

        tasks = []
        for item in datasets:
            download_url = item.get("download_url")
            if download_url:
                tasks.append(
                    self.fetch_and_process_yaml(
                        http_client, download_url, item.get("name")
                    )
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        final_results = []
        for res in results:
            if isinstance(res, Exception):
                self.application.settings.get("logger", print)(f"Error en tarea: {res}")
            elif res:
                final_results.append(res)

        flattened = [obj for sublist in final_results for obj in sublist]

        try:
            result = {
                "cwd": {
                    "name": "Root",
                    "isFile": False,
                    "path": "/",
                    "hasChild": True,
                    "type": "folder",
                    "size": "-",
                    "dateModified": "-",
                },
                "files": flattened,
            }
            try:
                _set_cache(cache_key, result)
            except Exception as e:
                print(f"Error saving to cache: {e}")
            finally:
                session.close()
            return result
        except Exception as e:
            self.set_status(500)
            return json.dumps({"error": "Error downloading public buckets:" + str(e)})

    def extract_bucket_name(self, arn: str) -> str:
        """
        Extracts the bucket name from an ARN (Amazon Resource Name).

        Args:
            arn (str): The ARN string to extract the bucket name from.

        Returns:
            str: The extracted bucket name or an empty string if invalid.
        """
        if not arn:
            return ""
        prefix = "arn:aws:s3:::"
        if arn.startswith(prefix):
            arn = arn[len(prefix) :]
        parts = [p for p in arn.split("/") if p]
        return parts[-1] if parts else arn

    async def fetch_and_process_yaml(self, http_client, url, filename):
        """
        Downloads and processes a YAML file to extract public S3 bucket information.

        Args:
            http_client (tornado.httpclient.AsyncHTTPClient): The HTTP client to fetch the file.
            url (str): URL of the YAML file.
            filename (str): Name of the file being processed.

        Returns:
            list: A list of dictionaries containing public bucket details.
        """
        try:
            response = await http_client.fetch(url)
            yaml_text = response.body.decode()
            data = yaml.safe_load(yaml_text)
        except Exception as e:
            return {"file": filename, "error": str(e)}

        resources = data.get("Resources", [])
        buckets = [
            {
                "Description": resource.get("Description"),
                "ARN": resource.get("ARN"),
                "Region": resource.get("Region"),
                "Type": resource.get("Type"),
            }
            for resource in resources
            if "s3 bucket" in resource.get("Type", "").lower()
        ]

        files_list = []
        for bucket in buckets:
            arn = bucket.get("ARN")
            if not arn:
                continue
            bucket_name = self.extract_bucket_name(arn)
            bucket_region = bucket.get("Region")
            file_obj = {
                "name": bucket_name,
                "isFile": False,
                "path": f"/{bucket_name}/",
                "hasChild": True,
                "type": "folder",
                "size": "-",
                "dateModified": "-",
                "region": bucket_region,
            }
            files_list.append(file_obj)

        return files_list

    def _list_bucket_contents(self, s3_client, path, client_type):
        """
        Lists the contents of a given S3 bucket.

        Args:
            s3_client (botocore.client.S3): The S3 client.
            path (str): The path to list contents from.
            client_type (str): Type of client ('private' or 'public').

        Returns:
            str: JSON-encoded list of bucket contents.
        """
        sanitized = path.lstrip("/")
        parts = sanitized.split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        if client_type == "private":
            try:
                s3_client.head_bucket(Bucket=bucket_name)
            except ClientError:
                self.set_status(403)
                return json.dumps(
                    {
                        "error": f"You do not have permission to access the bucket {bucket_name}."
                    }
                )
        try:
            items = list_bucket_contents(s3_client, bucket_name, prefix)
            cwd_name = prefix.split("/")[-1] if prefix else bucket_name
            cwd_path = f"/{bucket_name}/{prefix}".rstrip("/")
            if not cwd_path:
                cwd_path = f"/{bucket_name}/"
            cwd = format_item(cwd_name, False, cwd_path, True, "folder")
            return json.dumps({"cwd": cwd, "files": items})
        except Exception as e:
            self.set_status(500)
            return json.dumps({"error": str(e)})

    def _download_file(self, data, s3_client):
        """
        Downloads a file from S3 and saves it locally.

        Args:
            data (dict): Request data containing download details.
            s3_client (botocore.client.S3): The S3 client used to download the file.

        Raises:
            403: If the user does not have permission to download the file.
            500: If an error occurs during download.
        """
        try:
            downloads_folder = data.get("downloadsFolder", DOWNLOADS_DIR)
            if data.get("data") and len(data.get("data")) > 0:
                file_full_path = data["data"][0].get("path")
            else:
                file_full_path = os.path.join(
                    data.get("path", ""), data.get("names", [""])[0]
                )
            file_path = file_full_path.strip("/")
            parts = file_path.split("/", 1)
            if len(parts) < 2:
                self.set_status(400)
                self.write(
                    json.dumps(
                        {"error": "The file path must follow the format 'bucket/key'"}
                    )
                )
                return
            bucket_name, key = parts
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            file_content = response["Body"].read()
            os.makedirs(downloads_folder, exist_ok=True)
            local_file_path = os.path.join(downloads_folder, os.path.basename(key))
            with open(local_file_path, "wb") as f:
                f.write(file_content)
            self.write(json.dumps({"success": True, "file_saved": local_file_path}))
        except ClientError:
            self.set_status(403)
            self.write(
                json.dumps(
                    {"error": "You do not have permission to download this file."}
                )
            )
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))

    def _get_details(self, data, s3_client):
        """
        Retrieves details of a file or folder from S3.

        Args:
            data (dict): Request data containing file or folder details.
            s3_client (botocore.client.S3): The S3 client used to get the details.

        Raises:
            400: If required parameters are missing.
            403: If the user does not have permission to access the bucket.
            500: If an error occurs while fetching details.
        """
        try:
            items = data.get("data", [])
            if not items:
                self.set_status(400)
                self.write(json.dumps({"error": "The 'data' parameter is required."}))
                return
            details = []
            for item in items:
                full_path = item.get("path", "").strip("/")
                if not full_path:
                    continue
                parts = full_path.split("/", 1)
                bucket_name = parts[0]
                object_key = parts[1] if len(parts) > 1 else ""
                try:
                    if s3_client.meta.config.signature_version != UNSIGNED:
                        s3_client.head_bucket(Bucket=bucket_name)
                except ClientError:
                    self.set_status(403)
                    self.write(
                        json.dumps(
                            {
                                "error": f"You do not have permission to access the bucket {bucket_name}."
                            }
                        )
                    )
                    return
                if not object_key or object_key.endswith("/"):
                    folder_detail = format_item(
                        item.get("name"),
                        False,
                        f"/{bucket_name}/{object_key}",
                        True,
                        "folder",
                    )
                    details.append(folder_detail)
                else:
                    try:
                        response = s3_client.head_object(
                            Bucket=bucket_name, Key=object_key
                        )
                        last_modified = response.get("LastModified")
                        date_mod_str = (
                            last_modified.isoformat() if last_modified else ""
                        )
                        file_detail = format_item(
                            item.get("name"),
                            True,
                            f"/{bucket_name}/{object_key}",
                            False,
                            "file",
                            response.get("ContentLength", 0),
                            date_mod_str,
                        )
                        details.append(file_detail)
                    except ClientError as e:
                        code = e.response["Error"]["Code"]
                        if code in ["404", "NoSuchKey"]:
                            folder_detail = format_item(
                                item.get("name"),
                                False,
                                f"/{bucket_name}/{object_key}/",
                                True,
                                "folder",
                            )
                            details.append(folder_detail)
                        else:
                            self.set_status(403)
                            self.write(
                                json.dumps(
                                    {
                                        "error": f"You do not have permission to access the object {object_key}."
                                    }
                                )
                            )
                            return
            self.write(json.dumps({"details": details[0] if details else {}}))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"error": "Internal server error: " + str(e)}))

    async def _search_items(self, data, s3_client, client_type):
        """
        Searches for items in S3 buckets.

        This method searches for matching items either in the root (buckets) or within
        a specified bucket.

        Args:
            data (dict): Request data containing the search string and path.
            s3_client (botocore.client.S3): The S3 client.
            client_type (str): Type of client ('private' or 'public').

        Returns:
            str: JSON-encoded search results.
        """
        search_text = data.get("searchString", "").replace("*", "").lower()

        if not search_text:
            self.set_status(400)
            return json.dumps({"error": "The 'searchString' parameter is required."})

        path = data.get("path", "").strip()

        if not path or path == "/":
            if client_type == "private":
                try:
                    response = s3_client.list_buckets()
                    buckets = []
                    for bucket in response.get("Buckets", []):
                        name = bucket.get("Name", "")
                        if search_text in name.lower():
                            buckets.append(
                                format_item(name, False, f"/{name}/", True, "folder")
                            )
                    cwd = format_item("Root", False, "/", True, "folder")
                    return json.dumps({"cwd": cwd, "files": buckets})
                except Exception as e:
                    self.set_status(500)
                    return json.dumps({"error": str(e)})
            else:
                public_buckets_str = await self._list_public_buckets()
                try:

                    if not isinstance(public_buckets_str, dict):
                        public_buckets_data = json.loads(public_buckets_str)
                    else:
                        public_buckets_data = public_buckets_str
                except Exception as e:
                    self.set_status(500)
                    return json.dumps(
                        {"error": "Error parsing the list of public buckets:" + str(e)}
                    )
                filtered = [
                    item
                    for item in public_buckets_data.get("files", [])
                    if search_text in item.get("name", "").lower()
                ]
                cwd = public_buckets_data.get(
                    "cwd", format_item("Root", False, "/", True, "folder")
                )
                return json.dumps({"cwd": cwd, "files": filtered})
        else:
            sanitized = path.lstrip("/")
            parts = sanitized.split("/", 1)
            bucket_name = parts[0]
            prefix = parts[1] if len(parts) > 1 else ""
            try:
                if client_type == "private":
                    try:
                        s3_client.head_bucket(Bucket=bucket_name)
                    except ClientError:
                        self.set_status(403)
                        return json.dumps(
                            {
                                "error": f"You do not have permission to access the bucket {bucket_name}."
                            }
                        )
                list_params = {
                    "Bucket": bucket_name,
                    "Prefix": prefix,
                    "Delimiter": "/",
                }
                response = s3_client.list_objects_v2(**list_params)
                matching_files = []
                matching_folders = []
                for obj in response.get("Contents", []):
                    key = obj.get("Key", "")
                    if search_text in key.lower():
                        file_name = key.split("/")[-1]
                        size = obj.get("Size", 0)
                        last_modified = obj.get("LastModified")
                        date_modified = (
                            last_modified.isoformat() if last_modified else ""
                        )
                        matching_files.append(
                            format_item(
                                file_name,
                                True,
                                f"/{bucket_name}/{key}",
                                False,
                                "file",
                                size,
                                date_modified,
                            )
                        )
                for common_prefix in response.get("CommonPrefixes", []):
                    folder_prefix = common_prefix.get("Prefix", "")
                    if search_text in folder_prefix.lower():
                        folder_name = folder_prefix.rstrip("/").split("/")[-1]
                        matching_folders.append(
                            format_item(
                                folder_name,
                                False,
                                f"/{bucket_name}/{folder_prefix}",
                                True,
                                "folder",
                            )
                        )
                cwd_name = prefix.split("/")[-1] if prefix else bucket_name
                cwd_path = f"/{bucket_name}/{prefix}".rstrip("/")
                if not cwd_path:
                    cwd_path = f"/{bucket_name}/"
                cwd = format_item(cwd_name, False, cwd_path, True, "folder")
                return json.dumps(
                    {"cwd": cwd, "files": matching_folders + matching_files}
                )
            except Exception as e:
                self.set_status(500)
                return json.dumps({"error": str(e)})
