import argparse
import json
import sys
import time
from urllib import error, request


def _get_json(url: str, timeout: float = 5.0) -> dict:
    with request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _ready(qdrant_url: str, infinity_url: str) -> tuple[bool, str]:
    try:
        _get_json(f"{qdrant_url.rstrip('/')}/collections")
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return False, f"Qdrant is not ready: {exc}"

    try:
        models = _get_json(f"{infinity_url.rstrip('/')}/models")
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return False, f"Infinity is not ready: {exc}"

    deployed = {item.get("id") for item in models.get("data", []) if isinstance(item, dict)}
    required = {"jina-embeddings-v5-text-small", "jina-reranker-v3"}
    missing = sorted(required - deployed)
    if missing:
        return False, f"Infinity models are not ready: {', '.join(missing)}"
    return True, "ready"


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait until Qdrant and Infinity are ready.")
    parser.add_argument("--qdrant-url", default="http://qdrant:6333")
    parser.add_argument("--infinity-url", default="http://infinity:7997")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()

    deadline = time.monotonic() + args.timeout
    last_message = ""
    while time.monotonic() < deadline:
        ok, message = _ready(args.qdrant_url, args.infinity_url)
        if ok:
            print("Semantic services are ready.", flush=True)
            return 0
        if message != last_message:
            print(message, flush=True)
            last_message = message
        time.sleep(args.interval)

    print(f"Timed out waiting for semantic services: {last_message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
