"""A local HTTP server that answers from scripted responses and records every request."""

import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType
from typing import Any, final


@dataclass(frozen=True)
class Answer:
    """One scripted response."""

    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    delay: float = 0.0


@dataclass(frozen=True)
class Recorded:
    """One request the server received; header names are lowercased."""

    method: str
    path: str
    headers: dict[str, str]
    body: bytes


@final
class FakeServer:
    """Answer each path from its scripted answers in turn (the last one repeats); other paths get 404."""

    def __init__(self) -> None:
        self.requests: list[Recorded] = []
        self._answers: dict[str, list[Answer]] = {}
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_class())
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, args=(0.01,), daemon=True)

    @property
    def host(self) -> str:
        """Return the server's host:port."""
        return f"127.0.0.1:{self._server.server_address[1]}"

    @property
    def url(self) -> str:
        """Return the server's base URL."""
        return f"http://{self.host}"

    def answer(self, path: str, *answers: Answer) -> None:
        """Script the answers for path."""
        with self._lock:
            self._answers[path] = list(answers)

    def requests_to(self, path: str) -> list[Recorded]:
        """Return the recorded requests for path."""
        with self._lock:
            return [request for request in self.requests if request.path == path]

    def _next(self, path: str) -> Answer:
        with self._lock:
            queue = self._answers.get(path)
            if not queue:
                return Answer(404)
            return queue.pop(0) if len(queue) > 1 else queue[0]

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                """Stay silent, so the test output stays clean."""

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                headers = {name.lower(): value for name, value in self.headers.items()}
                with server._lock:
                    server.requests.append(Recorded(self.command, self.path, headers, body))
                answer = server._next(self.path)
                if answer.delay:
                    time.sleep(answer.delay)
                self.send_response(answer.status)
                for name, value in answer.headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(answer.body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(answer.body)

            do_GET = _handle
            do_POST = _handle
            do_HEAD = _handle

        return Handler

    def __enter__(self) -> "FakeServer":
        self._thread.start()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self._server.shutdown()
        self._server.server_close()
