from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from science_researcher.embedding_openai import OpenAIEmbeddingProvider


class _EmbeddingHandler(BaseHTTPRequestHandler):
    request_payload: dict[str, object] = {}

    def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
        length = int(self.headers["Content-Length"])
        _EmbeddingHandler.request_payload = json.loads(self.rfile.read(length).decode("utf-8"))
        body = json.dumps({"data": [{"embedding": [0.1, 0.2, 0.3]}]})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # pragma: no cover
        return


class OpenAIEmbeddingProviderTests(unittest.TestCase):
    def test_posts_to_embeddings_endpoint_with_dimensions(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _EmbeddingHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            provider = OpenAIEmbeddingProvider(
                api_key="test-key",
                base_url=f"http://127.0.0.1:{server.server_port}/v1",
                model="text-embedding-3-small",
                dimensions=512,
            )
            self.assertEqual(provider.embed("local positivity"), [0.1, 0.2, 0.3])
            self.assertEqual(_EmbeddingHandler.request_payload["model"], "text-embedding-3-small")
            self.assertEqual(_EmbeddingHandler.request_payload["dimensions"], 512)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
