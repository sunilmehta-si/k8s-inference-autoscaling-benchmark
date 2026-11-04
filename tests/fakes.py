"""A fake OpenAI-compatible streaming server, for the client's tests."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class RoomyServer(ThreadingHTTPServer):
    # The default listen backlog of 5 drops connections when a burst of requests arrives at once, and the client
    # reports them as failures that are the test server's, not the client's.
    request_queue_size = 128
    daemon_threads = True


class FakeModelServer:
    """Answers every chat completion after `first_token_s`, streaming the requested number of chunks.

    `status` makes it answer with that HTTP status and no stream. The bodies it received are kept in `requests`."""

    def __init__(self, first_token_s: float = 0.0, chunk_s: float = 0.0, status: int = 200, chunks: int | None = None):
        self.first_token_s, self.chunk_s, self.status, self.chunks = first_token_s, chunk_s, status, chunks
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep the test output quiet
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(payload)
                if outer.status != 200:
                    self.send_response(outer.status)
                    self.end_headers()
                    self.wfile.write(b"overloaded")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                time.sleep(outer.first_token_s)
                count = outer.chunks if outer.chunks is not None else payload["max_tokens"]
                for i in range(count):
                    if i:
                        time.sleep(outer.chunk_s)
                    self.wfile.write(b"data: " + json.dumps({"choices": [{"delta": {"content": "x"}}]}).encode() + b"\n\n")
                    self.wfile.flush()
                usage = {"choices": [], "usage": {"prompt_tokens": len(payload["messages"][0]["content"].split()),
                                                  "completion_tokens": count}}
                self.wfile.write(b"data: " + json.dumps(usage).encode() + b"\n\ndata: [DONE]\n\n")

        self.server = RoomyServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
