"""Send one authenticated synthetic request to a Layaas API deployment."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Private API URL returned by the OCI stack")
    parser.add_argument("--health", action="store_true", help="Check authenticated readiness")
    parser.add_argument("--sample", type=Path, help="Synthetic JSON input (default: Swedish example)")
    args = parser.parse_args()
    key = os.environ.get("LAYA_API_KEY")
    if not key:
        print("Set LAYA_API_KEY through your approved secret injection method", file=sys.stderr)
        return 2
    if len(key) < 32 or not key.isascii() or any(character.isspace() for character in key):
        print("LAYA_API_KEY is malformed; credential value suppressed", file=sys.stderr)
        return 2

    headers = {
        "Authorization": "Bearer " + key,
        "Accept": "application/json",
        "User-Agent": "Layaas-Python-Client/1.0",
    }
    if args.health:
        path, body = "/health", None
    else:
        sample_path = args.sample or Path("samples/typed-sv.json")
        body = json.dumps(json.loads(sample_path.read_text(encoding="utf-8"))).encode("utf-8")
        path = "/v1/systemone"
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(args.base_url.rstrip("/") + path, data=body, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            result = json.loads(response.read(1_048_576))
    except urllib.error.HTTPError as error:
        print(f"Layaas returned HTTP {error.code}; response body suppressed", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        print(f"Layaas request failed ({type(error).__name__}); details suppressed", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
