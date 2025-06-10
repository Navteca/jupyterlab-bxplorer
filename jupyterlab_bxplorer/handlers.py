"""
HTTP Handlers for JupyterLab Bxplorer v2 Extension.

This module defines API handlers for the JupyterLab Bxplorer v2 extension.
It includes base handlers for setting CORS headers and managing routes,
as well as example endpoints for file operations.
"""

import json
import tornado
import tornado.web
from jupyter_server.base.handlers import APIHandler
from jupyter_server.serverapp import ServerApp
from jupyter_server.utils import url_path_join
from .file_manager_handler import FileManagerHandler
from .download_history_handler import DownloadHistoryHandler
from .favorites_handler import FavoritesHandler
from .config_handler import ConfigHandler

from .favorites import Base, engine

Base.metadata.create_all(engine)


class BaseHandler(APIHandler):
    """
    Base handler that extends APIHandler to provide default CORS headers
    and common behavior for handling OPTIONS requests.
    """

    def data_received(self, chunk):
        """
        Override required by the base class RequestHandler.
        This method is not used in this handler, as the handler does not process streaming data.
        """

    def set_default_headers(self):
        """
        Sets the default headers for CORS (Cross-Origin Resource Sharing).

        Allows any domain to access the API and specifies allowed headers and methods.
        """
        # Allow any domain to access your API
        self.set_header("Access-Control-Allow-Origin", "*")
        # List the allowed headers
        self.set_header(
            "Access-Control-Allow-Headers",
            "x-requested-with, content-type, Authorization",
        )
        # List the allowed methods
        self.set_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
        )

    def options(self, *args, **kwargs):
        """
        Handles HTTP OPTIONS requests by returning a 204 (No Content) response.
        """
        # no body is sent for an OPTIONS request
        self.set_status(204)
        self.finish()


class RouteHandler(BaseHandler):
    """
    A simple route handler for demonstration purposes.

    This handler returns a JSON response indicating that the example endpoint is working.
    """

    @tornado.web.authenticated
    def get(self):
        """
        Handles GET requests and returns a JSON response indicating the endpoint's functionality.
        """
        self.finish(
            json.dumps(
                {"data": "This is /jupyterlab-bxplorer/get-example endpoint!"}
            )
        )


def setup_handlers(web_app: ServerApp) -> None:
    """
    Configures URL handlers for the JupyterLab Bxplorer v2 extension.

    Registers endpoints for the example route and file operations.

    Args:
        web_app (ServerApp): The Jupyter server application instance.
    """
    host_pattern = ".*$"

    base_path = url_path_join(web_app.settings["base_url"], "jupyterlab-bxplorer")
    handlers = [
        (url_path_join(base_path, "get-example"), RouteHandler),
        (url_path_join(base_path, "FileOperations"), FileManagerHandler),
        (url_path_join(base_path, "download_history"), DownloadHistoryHandler),
        (url_path_join(base_path, "favorites"), FavoritesHandler),
        (url_path_join(base_path, "config"), ConfigHandler),
    ]
    web_app.add_handlers(host_pattern, handlers)
