import json
from typing import Any
from urllib import error, request


class HttpServiceError(RuntimeError):
    """Raised when an external HTTP service cannot complete a request."""


def request_json(method: str, url: str, *, payload: dict[str, Any] | None = None, timeout: float = 20.0) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HttpServiceError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise HttpServiceError(f"{method} {url} failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise HttpServiceError(f"{method} {url} timed out") from exc

    if not body:
        return {}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HttpServiceError(f"{method} {url} returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise HttpServiceError(f"{method} {url} returned non-object JSON")
    return parsed
