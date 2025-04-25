import json
from jupyter_server.base.handlers import APIHandler
from .favorites import add_favorite, remove_favorite, list_favorites


class FavoritesHandler(APIHandler):
    def post(self):
        """Add a bucket to favorites."""
        try:
            data = json.loads(self.request.body.decode("utf-8"))
            bucket = data.get("bucket")
            is_private = data.get("client_type") == "private"
            if not bucket:
                raise ValueError("Missing bucket name")
            add_favorite(bucket, is_private)
            self.write({"status": "ok", "message": f"{bucket} added to favorites"})
        except Exception as e:
            self.set_status(400)
            self.write({"error": str(e)})

    def delete(self):
        """Remove a bucket from favorites."""
        try:
            data = json.loads(self.request.body.decode("utf-8"))
            bucket = data.get("bucket")
            if not bucket:
                raise ValueError("Missing bucket name")
            remove_favorite(bucket)
            self.write({"status": "ok", "message": f"{bucket} removed from favorites"})
        except Exception as e:
            self.set_status(400)
            self.write({"error": str(e)})

    def get(self):
        """List all favorite buckets or datasets, formatted for FileManager."""
        try:
            favorites = list_favorites()
            files = []
            for fav in favorites:
                path = fav.get("path", "").strip("/")
                segments = path.split("/")
                if segments[0].endswith(".yaml"):
                    # Favorito es un dataset público
                    name = segments[0]
                    files.append(
                        {
                            "name": name,
                            "isFile": False,
                            "path": f"/{name}/",
                            "hasChild": True,
                            "type": "folder",
                            "size": "-",
                            "dateModified": "-",
                        }
                    )
                else:
                    # Bucket privado
                    name = segments[0]
                    files.append(
                        {
                            "name": name,
                            "isFile": False,
                            "path": f"/{name}/",
                            "hasChild": True,
                            "type": "folder",
                            "size": "-",
                            "dateModified": "-",
                        }
                    )
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
                "files": files,
            }
            self.write(result)
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})
