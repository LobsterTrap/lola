"""Local HTTP server for serving marketplace catalogs during E2E tests."""

import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class LocalHTTPServer:
    """Ephemeral HTTP server on localhost for serving marketplace catalogs in tests."""

    def __init__(self, directory: Path):
        """Bind to a random port and prepare to serve files from directory."""
        self.directory = directory
        handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        """Start serving in a daemon thread."""
        self.thread.start()

    def stop(self) -> None:
        """Shut down the server and release the port."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
