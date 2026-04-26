import argparse
import hashlib
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

DEFAULT_MODEL = "mospoli-hash-embeddings-v1"
DEFAULT_DIMENSIONS = 384


def embed_text(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    normalized = " ".join(text.casefold().split())
    features = _features(normalized)
    if not features:
        return vector

    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        raw = int.from_bytes(digest, "big")
        index = raw % dimensions
        sign = 1.0 if ((raw >> 8) & 1) else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def _features(text: str) -> list[str]:
    tokens = [token for token in text.replace("/", " ").replace("-", " ").split() if token]
    features: list[str] = []
    for token in tokens:
        features.append(f"tok:{token}")
        features.extend(f"tri:{token[index : index + 3]}" for index in range(max(1, len(token) - 2)))
    features.extend(f"char:{text[index : index + 4]}" for index in range(max(1, len(text) - 3)))
    return features


class SemanticRuntimeHandler(BaseHTTPRequestHandler):
    server_version = "MOSPOLISemanticRuntime/1.0"

    def do_GET(self) -> None:
        if self.path.rstrip("/") in {"/models", "/v1/models"}:
            server = cast(SemanticRuntimeServer, self.server)
            self._send_json({"data": [{"id": server.model_name, "object": "model"}]})
            return
        if self.path.rstrip("/") in {"", "/health"}:
            self._send_json({"status": "ok"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path.rstrip("/") not in {"/embeddings", "/v1/embeddings"}:
            self.send_error(404)
            return

        try:
            server = cast(SemanticRuntimeServer, self.server)
            payload = self._read_json()
            raw_input = payload.get("input", "")
            texts = raw_input if isinstance(raw_input, list) else [raw_input]
            embeddings = [embed_text(str(text), server.dimensions) for text in texts]
            self._send_json(
                {
                    "object": "list",
                    "model": payload.get("model") or server.model_name,
                    "data": [{"object": "embedding", "index": index, "embedding": embedding} for index, embedding in enumerate(embeddings)],
                }
            )
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=400)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object.")
        return payload

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class SemanticRuntimeServer(ThreadingHTTPServer):
    model_name: str
    dimensions: int


def main() -> int:
    parser = argparse.ArgumentParser(description="Lightweight OpenAI-compatible embedding runtime for MOSPOLI_LMS.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7997)
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    args = parser.parse_args()

    server = SemanticRuntimeServer((args.host, args.port), SemanticRuntimeHandler)
    server.model_name = args.model_name
    server.dimensions = args.dimensions
    print(f"Semantic runtime ready on {args.host}:{args.port} model={args.model_name} dimensions={args.dimensions}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
