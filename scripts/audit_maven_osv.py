"""Query OSV for public Maven coordinates from extracted Gradle trees."""

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from extract_gradle_runtime import coordinates

URL = "https://api.osv.dev/v1/querybatch"


def collect(pairs, send):
    results = {pair: set() for pair in pairs}
    pending = [(pair, None) for pair in pairs]
    seen_tokens = set()
    while pending:
        requests = [{"package": {"ecosystem": "Maven", "name": name}, "version": version,
                     **({"page_token": token} if token else {})} for (name, version), token in pending]
        response = send({"queries": requests})
        rows = response.get("results") if isinstance(response, dict) else None
        if not isinstance(rows, list) or len(rows) != len(pending):
            raise ValueError("Incomplete OSV response")
        following = []
        for (pair, _), row in zip(pending, rows, strict=True):
            if not isinstance(row, dict) or not isinstance(row.get("vulns", []), list):
                raise ValueError("Invalid OSV result")
            for vulnerability in row.get("vulns", []):
                if not isinstance(vulnerability, dict) or not isinstance(vulnerability.get("id"), str):
                    raise ValueError("Invalid OSV vulnerability")
                results[pair].add(vulnerability["id"])
            token = row.get("next_page_token")
            if token is not None:
                if not isinstance(token, str) or not token or (pair, token) in seen_tokens or len(seen_tokens) >= 500:
                    raise ValueError("Invalid or repeating OSV page token")
                seen_tokens.add((pair, token))
                following.append((pair, token))
        pending = following
    return results


def post(payload):
    request = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trees", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = {path.name: path.read_bytes() for path in args.trees}
    if len(inputs) != len(args.trees):
        raise ValueError("Duplicate inventory names")
    pairs = sorted({pair for raw in inputs.values() for pair in coordinates(raw.decode("utf-8"))})
    if not pairs or len(pairs) > 1000:
        raise ValueError("Unexpected number of Maven coordinates")
    hits = collect(pairs, post)
    output = {"queried_at_utc_local_clock": datetime.now(timezone.utc).isoformat(),
              "source": URL, "ecosystem": "Maven", "count": len(pairs),
              "inventories": {name: hashlib.sha256(raw).hexdigest() for name, raw in inputs.items()},
              "packages": [{"name": name, "version": version, "vulnerability_ids": sorted(hits[(name, version)])}
                           for name, version in pairs]}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"Queried {len(pairs)} Maven coordinates; {sum(bool(ids) for ids in hits.values())} have OSV hits.")


if __name__ == "__main__":
    main()
