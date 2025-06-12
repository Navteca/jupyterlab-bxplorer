"""
config_handler.py

This module defines an API handler for serving configuration data required by
the JupyterLab Bxplorer extension.
It retrieves environment-based configuration and returns it as a JSON response.
"""
import os
import json
from jupyter_server.base.handlers import APIHandler


class ConfigHandler(APIHandler):
    """
    API handler for retrieving the Bxplorer configuration.

    This handler reads the required configuration from environment variables and
    responds with the configuration data in JSON format.
    """

    def data_received(self, chunk):
        """
        Override required by the base class RequestHandler.
        This method is not used in this handler, as the handler does not process streaming data.
        """

    def get(self):
        """
        Handle GET requests to retrieve the BXPLORER_CONFIG environment variable.

        Returns:
            JSON response containing the license configuration or an error message with status
            code 500 if the variable is missing.
        """
        try:
            license_path = os.path.expanduser('/etc/bxplorer/license.txt')
            with open(license_path, 'r', encoding='utf-8') as file:                
                license_key = file.read()

            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({"license": license_key}))
        except EnvironmentError as e:
            self.set_status(500)
            self.write(json.dumps({"error": str(e)}))
