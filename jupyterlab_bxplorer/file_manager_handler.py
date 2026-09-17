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
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import asyncio
import yaml

import tornado.web
import tornado.httpclient

import boto3
from botocore.exceptions import ClientError
from botocore import UNSIGNED
from botocore.config import Config

from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from jupyter_server.base.handlers import APIHandler
from .download_history import (
    DownloadHistory,
    insert_download_history,
    update_download_history,
)

from .favorites import list_favorites

download_executor = ThreadPoolExecutor(max_workers=5)
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
    "sqlite:///.cache.db", echo=False, connect_args={"check_same_thread": False}
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
        serialized_value = json.dumps(value)
        timestamp = time.time()

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
                return json.loads(cache_entry.value)
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
        return boto3.client("s3")


def format_size(bytes):
    """
    Converts byte size to a human-readable format (KB, MB, GB).

    Args:
        bytes (int): Size in bytes.

    Returns:
        str: Human-readable string representation of the size.
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
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
        # Determine region: treat unsigned (public) clients uniformly, handling both constant and string forms
        sig = getattr(s3_client.meta.config, "signature_version", None)
        if sig == UNSIGNED or sig == "unsigned":
            region = "us-east-1"
        else:
            try:
                loc_resp = s3_client.get_bucket_location(Bucket=bucket_name)
                location = loc_resp.get("LocationConstraint")
                region = location if location else "us-east-1"
            except ClientError as e:
                region = "us-east-1"
                logger = globals().get("logger", print)
                logger(f"Warning: could not get location for bucket {bucket_name}, defaulting to us-east-1: {e}")

        list_params = {"Bucket": bucket_name, "Prefix": prefix, "Delimiter": "/"}
        if continuation_token:
            list_params["ContinuationToken"] = continuation_token

        response = s3_client.list_objects_v2(**list_params)

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

    def data_received(self, chunk):
        """
        Override required by the base class RequestHandler.
        This method is not used in this handler, as the handler does not process streaming data.
        """

    @tornado.web.authenticated
    async def post(self):
        """
        Handles POST requests for FileManager actions such as read, download, details, and search.

        The request should include a JSON body with an "action" field specifying the operation to
        perform:
        - "read": List buckets or contents within a bucket.
        - "download": Download a file from S3.
        - "details": Retrieve metadata for a file or folder.
        - "search": Search for files/folders in S3.

        Returns:
            JSON response with the result of the requested action.
        """
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

        action = data.get("action", "").lower()
        path = data.get("path", "").strip()
        client_type = data.get("client_type", "public").lower()
        # Reinterpretar client_type cuando proviene de favoritos
        if client_type == "favorites":
            if path and path.strip("/").split("/")[0].endswith(".yaml"):
                client_type = "public"
            else:
                client_type = "private"
        s3_client = get_s3_client(client_type)

        if action == "read":
            path = data.get("path", "").strip()
            client_type = data.get("client_type", "public").lower()
            s3_client = get_s3_client(client_type)
            if not path or path == "/":
                if client_type == "private":
                    result = self._list_private_buckets(s3_client)
                elif client_type == "public":
                    result = await self._list_public_datasets()  # usar el nuevo método
                else:
                    favorites = list_favorites()
                    processed = []
                    for fav in favorites:
                        fav_path = fav.get("path", "").strip("/")
                        segments = fav_path.split("/")
                        if len(segments) >= 3 and segments[0].endswith(".yaml"):
                            # Formato dataset.yaml/bucket/key
                            dataset = segments[0]
                            bucket = segments[1]
                            name = segments[-1]
                            is_file = "." in name
                            processed.append(
                                format_item(
                                    name,
                                    is_file,
                                    f"/{fav_path}",
                                    not is_file,
                                    "file" if is_file else "folder",
                                )
                            )
                        elif len(segments) >= 2:
                            # Formato bucket/key
                            bucket = segments[0]
                            name = segments[-1]
                            is_file = "." in name
                            processed.append(
                                format_item(
                                    name,
                                    is_file,
                                    f"/{fav_path}",
                                    not is_file,
                                    "file" if is_file else "folder",
                                )
                            )
                        else:
                            # Bucket solo
                            bucket = segments[0]
                            processed.append(
                                format_item(
                                    bucket, False, f"/{bucket}/", True, "folder"
                                )
                            )
                    cwd = format_item("Root", False, "/", True, "folder")
                    result = {"cwd": cwd, "files": processed}
                self.set_header("Content-Type", "application/json")
                self.write(result)
            else:
                if client_type == "public":
                    # Determine if path refers to a dataset, even if extension omitted
                    sanitized = path.lstrip("/")
                    first_seg = sanitized.split("/", 1)[0]
                    datasets_cache = _get_from_cache("public_datasets_raw")
                    dataset_file = None
                    if first_seg.endswith(".yaml"):
                        dataset_file = first_seg
                    elif datasets_cache and any(ds.get("name") == first_seg + ".yaml" for ds in datasets_cache):
                        dataset_file = first_seg + ".yaml"

                    if dataset_file:
                        # Path refers to a dataset
                        dataset = dataset_file
                        # Obtener el resto del path (después del dataset)
                        rest = ""
                        if "/" in sanitized:
                            rest = sanitized.split("/", 1)[1]
                        if rest == "" or rest == "/":
                            # Nivel: buckets dentro del dataset
                            result = await self._list_buckets_in_dataset(dataset)
                        else:
                            # Caso: hay un bucket/prefijo dentro del dataset
                            bucket_name = rest.split("/", 1)[0]
                            prefix = ""
                            if "/" in rest:
                                prefix = rest.split("/", 1)[1]
                            try:
                                items = list_bucket_contents(s3_client, bucket_name, prefix)
                            except Exception as e:
                                self.set_status(500)
                                result = {"error": str(e)}
                                self.write(result)
                                return
                            # Ajustar paths de los items para incluir el dataset al frente
                            for item in items:
                                item_path = item.get("path", "")
                                if item_path.startswith(f"/{bucket_name}"):
                                    item["path"] = f"/{dataset}/{item_path.lstrip('/')}"
                            # Construir cwd con dataset+bucket
                            cwd_name = prefix.split("/")[-1] if prefix else bucket_name
                            cwd_path = f"/{dataset}/{bucket_name}/{prefix}".rstrip("/")
                            if not cwd_path.endswith("/"):
                                cwd_path += "/"
                            cwd = format_item(cwd_name, False, cwd_path, True, "folder")
                            result = {"cwd": cwd, "files": items}
                    else:
                        # Path público directo (no pertenece a ningún dataset)
                        result = self._list_bucket_contents(s3_client, path, client_type)
                else:
                    # Navegación de bucket privado (sin cambios)
                    result = self._list_bucket_contents(s3_client, path, client_type)

                self.set_header("Content-Type", "application/json")
                self.write(result)
        elif action == "download":
            downloads_folder = data.get("downloadsFolder", DOWNLOADS_DIR)
            if data.get("data") and len(data.get("data")) > 0:
                file_full_path = data["data"][0].get("path")
            else:
                file_full_path = os.path.join(
                    data.get("path", ""), data.get("names", [""])[0]
                )
            file_path = file_full_path.strip("/")
            segments = file_path.split("/")

            if len(segments) < 2:
                self.set_status(400)
                self.write(
                    json.dumps({"error": "Path must include at least bucket and key"})
                )
                return

            # Handle public datasets without explicit .yaml extension
            dataset_segment = segments[0]
            datasets_cache = _get_from_cache("public_datasets_raw")
            if client_type == "public":
                if (
                    not dataset_segment.endswith(".yaml")
                    and datasets_cache
                    and any(ds.get("name") == dataset_segment + ".yaml" for ds in datasets_cache)
                ):
                    dataset_segment = dataset_segment + ".yaml"

            # Determine bucket and key based on whether this is a dataset path
            if dataset_segment.endswith(".yaml"):
                # Format: dataset.yaml / bucket / key...
                if len(segments) < 3:
                    self.set_status(400)
                    self.write(
                        json.dumps(
                            {"error": "Path must include dataset.yaml, bucket and key"}
                        )
                    )
                    return
                bucket_name = segments[1]
                key = "/".join(segments[2:])
            else:
                # Classic format: bucket / key...
                bucket_name = segments[0]
                key = "/".join(segments[1:])

            os.makedirs(downloads_folder, exist_ok=True)
            local_file_path = os.path.join(downloads_folder, os.path.basename(key))

            download_id = insert_download_history(
                bucket=bucket_name, key=key, local_path=local_file_path
            )

            asyncio.get_running_loop().run_in_executor(
                download_executor,
                self._execute_download,
                bucket_name,
                key,
                local_file_path,
                download_id,
                client_type,
            )

            self.set_header("Content-Type", "application/json")
            self.write(
                json.dumps(
                    {
                        "status": "downloading",
                        "id": download_id,
                        "bucket": bucket_name,
                        "key": key,
                        "local_path": local_file_path,
                    }
                )
            )
            return
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
        # Remove duplicate buckets by name
        unique_buckets = []
        seen_names = set()
        for bucket in flattened:
            name = bucket.get("name")
            if name not in seen_names:
                seen_names.add(name)
                unique_buckets.append(bucket)
        flattened = unique_buckets

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

    async def _list_public_datasets(self):
        cache_key = "public_datasets"
        raw_cache_key = "public_datasets_raw"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        try:
            http_client = tornado.httpclient.AsyncHTTPClient()
            response = await http_client.fetch(PUBLIC_BUCKETS_URL)
            datasets_json = json.loads(response.body.decode())
        except Exception as e:
            self.set_status(500)
            return {"error": f"Error fetching dataset list: {e}"}

        # Construye lista de carpetas
        # Construye la respuesta para el frontend
        files = []
        for item in datasets_json:
            name = item.get("name")
            if not name.endswith(".yaml"):
                continue
            # Strip the .yaml extension for display purposes, but keep it in the path
            display_name = name[:-5] if name.endswith(".yaml") else name
            files.append(
                {
                    "name": display_name,
                    "isFile": False,
                    "path": f"/{name}/",
                    "hasChild": True,
                    "type": "folder",
                    "size": "-",
                    "dateModified": "-",
                }
            )

        cwd = {
            "name": "Root",
            "isFile": False,
            "path": "/",
            "hasChild": True,
            "type": "folder",
            "size": "-",
            "dateModified": "-",
        }
        result = {"cwd": cwd, "files": files}
        # Guarda en caché el JSON original y la respuesta formateada
        try:
            _set_cache(cache_key, {"cwd": cwd, "files": files})
            _set_cache(raw_cache_key, datasets_json)
        finally:
            session.close()

        return result

    async def _list_buckets_in_dataset(self, dataset_name):
        cache_key = f"public_buckets_{dataset_name}"
        cached = _get_from_cache(cache_key)
        if cached:
            return cached

        # Buscar el download_url del dataset en el JSON cacheado
        datasets_cache = _get_from_cache("public_datasets_raw")
        download_url = None

        if datasets_cache:
            for ds in datasets_cache:
                if ds.get("name") == dataset_name:
                    download_url = ds.get("download_url")
                    if not download_url or not download_url.startswith("http"):
                        self.set_status(500)
                        return {
                            "error": f"El dataset '{dataset_name}' tiene un download_url inválido."
                        }
                    break

        if not download_url:
            self.set_status(404)
            return {
                "error": f"No se encontró el dataset '{dataset_name}' o su download_url."
            }

        # Descargar y parsear YAML
        try:
            http_client = tornado.httpclient.AsyncHTTPClient()
            response = await http_client.fetch(download_url)
            yaml_text = response.body.decode()
            data = yaml.safe_load(yaml_text)
        except Exception as e:
            self.set_status(500)
            return {"error": f"Error loading dataset YAML: {e}"}

        resources = data.get("Resources", [])
        files = []
        for res in resources:
            res_type = res.get("Type", "")
            if res_type and "s3 bucket" in res_type.lower():
                arn = res.get("ARN", "")
                bucket_name = self.extract_bucket_name(arn)
                if not bucket_name:
                    continue
                region = res.get("Region", "")
                files.append(
                    {
                        "name": bucket_name,
                        "isFile": False,
                        "path": f"/{dataset_name}/{bucket_name}/",
                        "hasChild": True,
                        "type": "folder",
                        "size": "-",
                        "dateModified": "-",
                        "region": region,
                    }
                )

        cwd = {
            "name": dataset_name,
            "isFile": False,
            "path": f"/{dataset_name}/",
            "hasChild": True,
            "type": "folder",
            "size": "-",
            "dateModified": "-",
        }

        result = {"cwd": cwd, "files": files}

        try:
            _set_cache(cache_key, result)
        finally:
            session.close()

        return result

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

    async def _download_file(self, data, s3_client):
        """
        Downloads a file from S3 asynchronously in chunks and saves it locally,
        updating the download history.

        Args:
            data (dict): Request data containing download details.
            s3_client (botocore.client.S3): The S3 client used to download the file.
        """
        download_record = None
        try:
            downloads_folder = data.get("downloadsFolder", DOWNLOADS_DIR)
            if data.get("data") and len(data.get("data")) > 0:
                file_full_path = data["data"][0].get("path")
            else:
                file_full_path = os.path.join(
                    data.get("path", ""), data.get("names", [""])[0]
                )
            file_path = file_full_path.strip("/")
            segments = file_path.split("/")
            if len(segments) < 2:
                self.set_status(400)
                self.write(
                    json.dumps(
                        {"error": "The file path must include at least bucket and key"}
                    )
                )
                return

            if segments[0].endswith(".yaml"):
                # Formato: dataset.yaml / bucket / key...
                if len(segments) < 3:
                    self.set_status(400)
                    self.write(
                        json.dumps(
                            {
                                "error": "The file path must include dataset.yaml, bucket and key"
                            }
                        )
                    )
                    return
                bucket_name = segments[1]
                key = "/".join(segments[2:])
            else:
                # Formato clásico: bucket / key...
                bucket_name = segments[0]
                key = "/".join(segments[1:])

            # Retrieve the S3 object
            response = s3_client.get_object(Bucket=bucket_name, Key=key)
            os.makedirs(downloads_folder, exist_ok=True)
            local_file_path = os.path.join(downloads_folder, os.path.basename(key))

            # Insert a new download history record (assumes DownloadHistory model exists)
            download_record = DownloadHistory(
                bucket=bucket_name,
                key=key,
                status="downloading",
                start_time=time.time(),
            )
            session.add(download_record)
            session.commit()

            # Stream the file in chunks (1 MB per chunk)
            stream = response["Body"]
            chunk_size = 1024 * 1024  # 1 MB
            with open(local_file_path, "wb") as f:
                while True:
                    chunk = stream.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)

            # Update history record as successful
            download_record.status = "success"
            download_record.end_time = time.time()
            session.commit()

            self.write(json.dumps({"success": True, "file_saved": local_file_path}))
        except ClientError:
            if download_record is not None:
                download_record.status = "error"
                download_record.error_message = (
                    "You do not have permission to download this file."
                )
                download_record.end_time = time.time()
                session.commit()
            self.set_status(403)
            self.write(
                json.dumps(
                    {"error": "You do not have permission to download this file."}
                )
            )
        except Exception as e:
            if download_record is not None:
                download_record.status = "error"
                download_record.error_message = str(e)
                download_record.end_time = time.time()
                session.commit()
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
        a specified bucket or dataset.
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
                # MODIFICACIÓN: filtrar sobre datasets, no buckets
                public_datasets = _get_from_cache("public_datasets")
                if not public_datasets:
                    public_datasets = await self._list_public_datasets()

                filtered = [
                    item
                    for item in public_datasets.get("files", [])
                    if search_text in item.get("name", "").lower()
                ]
                cwd = public_datasets.get(
                    "cwd", format_item("Root", False, "/", True, "folder")
                )
                return json.dumps({"cwd": cwd, "files": filtered})
        else:
            sanitized = path.lstrip("/")
            segments = sanitized.split("/")
            if client_type == "public":
                if segments[0].endswith(".yaml"):
                    # Dentro de un dataset
                    dataset = segments[0]
                    # MODIFICACIÓN: soporto len(segments) == 1 o == 2 y segments[1] == ""
                    if len(segments) == 1 or (len(segments) == 2 and segments[1] == ""):
                        # Búsqueda a nivel de buckets dentro del dataset
                        dataset_buckets = await self._list_buckets_in_dataset(dataset)
                        filtered = [
                            b
                            for b in dataset_buckets.get("files", [])
                            if search_text in b.get("name", "").lower()
                        ]
                        cwd = dataset_buckets.get(
                            "cwd",
                            format_item(dataset, False, f"/{dataset}/", True, "folder"),
                        )
                        return json.dumps({"cwd": cwd, "files": filtered})
                    else:
                        # Búsqueda dentro de un bucket del dataset
                        bucket_name = segments[1]
                        prefix = "/".join(segments[2:]) if len(segments) > 2 else ""
                        list_params = {
                            "Bucket": bucket_name,
                            "Prefix": prefix,
                            "Delimiter": "/",
                        }
                        try:
                            response = s3_client.list_objects_v2(**list_params)
                            region = (
                                s3_client.get_bucket_location(Bucket=bucket_name).get(
                                    "LocationConstraint"
                                )
                                or "us-east-1"
                            )
                            matching_files = []
                            matching_folders = []
                            for obj in response.get("Contents", []):
                                key = obj.get("Key", "")
                                if search_text in key.lower():
                                    file_name = key.split("/")[-1]
                                    size = obj.get("Size", 0)
                                    last_modified = obj.get("LastModified")
                                    date_modified = (
                                        last_modified.isoformat()
                                        if last_modified
                                        else ""
                                    )
                                    matching_files.append(
                                        format_item(
                                            file_name,
                                            True,
                                            f"/{dataset}/{bucket_name}/{key}",
                                            False,
                                            "file",
                                            size,
                                            date_modified,
                                            region=region,
                                        )
                                    )
                            for common_prefix in response.get("CommonPrefixes", []):
                                folder_prefix = common_prefix.get("Prefix", "")
                                if search_text in folder_prefix.lower():
                                    folder_name = folder_prefix.rstrip("/").split("/")[
                                        -1
                                    ]
                                    matching_folders.append(
                                        format_item(
                                            folder_name,
                                            False,
                                            f"/{dataset}/{bucket_name}/{folder_prefix}",
                                            True,
                                            "folder",
                                            region=region,
                                        )
                                    )
                            cwd_name = prefix.split("/")[-1] if prefix else bucket_name
                            cwd_path = (
                                f"/{dataset}/{bucket_name}/{prefix}".rstrip("/") + "/"
                            )
                            cwd = format_item(cwd_name, False, cwd_path, True, "folder")
                            return json.dumps(
                                {"cwd": cwd, "files": matching_folders + matching_files}
                            )
                        except Exception as e:
                            self.set_status(500)
                            return json.dumps({"error": str(e)})
                else:
                    # comportamiento original para buckets fuera de datasets
                    bucket_name = segments[0]
                    prefix = "/".join(segments[1:]) if len(segments) > 1 else ""
                    try:
                        list_params = {
                            "Bucket": bucket_name,
                            "Prefix": prefix,
                            "Delimiter": "/",
                        }
                        response = s3_client.list_objects_v2(**list_params)
                        region = (
                            s3_client.get_bucket_location(Bucket=bucket_name).get(
                                "LocationConstraint"
                            )
                            or "us-east-1"
                        )
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
                                        region=region,
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
                                        region=region,
                                    )
                                )
                        cwd_name = prefix.split("/")[-1] if prefix else bucket_name
                        cwd_path = f"/{bucket_name}/{prefix}".rstrip("/") + "/"
                        cwd = format_item(cwd_name, False, cwd_path, True, "folder")
                        return json.dumps(
                            {"cwd": cwd, "files": matching_folders + matching_files}
                        )
                    except Exception as e:
                        self.set_status(500)
                        return json.dumps({"error": str(e)})
            else:
                # private bucket search (original logic)
                bucket_name = segments[0]
                prefix = "/".join(segments[1:]) if len(segments) > 1 else ""
                try:
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

    def _execute_download(self, bucket, key, local_path, record_id, client_type):
        """Helper function that downloads from S3 and updates history.
        Runs in a separate thread to avoid blocking the IOLoop."""
        s3_client = get_s3_client(client_type)
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            stream = response["Body"]
            chunk_size = 1024 * 1024  # 1 MB
            with open(local_path, "wb") as f:
                while True:
                    data = stream.read(chunk_size)
                    if not data:
                        break
                    f.write(data)
            update_download_history(record_id, status="success")
        except ClientError as e:
            update_download_history(
                record_id, status="error", error_message="S3 ClientError: " + str(e)
            )
        except Exception as e:
            update_download_history(record_id, status="error", error_message=str(e))
