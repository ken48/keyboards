from .encoding_setup import ensure_utf8_locale
from .logging_setup import setup_logging
from .socket_server import SocketServer
from .worker import Worker
from .menubar import run_app
from .warmup import warmup


def main():
    ensure_utf8_locale()
    setup_logging()

    # Import heavy deps once to avoid first-run latency.
    # Scripts themselves are NOT imported/executed here.
    warmup()

    worker = Worker()
    worker.start()

    server = SocketServer(worker)
    server.start()

    run_app(worker)
