#!/usr/bin/env python3
"""Run synthetic notebook-image widget tests without bundling fixtures into the app."""

import argparse
import base64
import json
import subprocess
import tempfile
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ("arbeitsblatt", "hefter", "arbeitsheft", "buchseite", "klassenarbeit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("vm", "chrome"), default="vm")
    parser.add_argument("--flutter", default="flutter")
    args = parser.parse_args()
    directory = ROOT / "testdata/notebook_synthetic"
    manifest = json.loads((directory / "manifest.json").read_text())
    entries = {row["name"]: row for row in manifest}
    if set(entries) != set(FILES) or len(manifest) != len(FILES):
        raise ValueError("unexpected synthetic fixture manifest")
    encoded = {}
    for name in FILES:
        entry = entries[name]
        if entry["file"] != name + ".jpg":
            raise ValueError("unexpected fixture name: " + name)
        content = (directory / entry["file"]).read_bytes()
        if not (
            content.startswith(b"\xff\xd8\xff")
            and content.endswith(b"\xff\xd9")
            and len(content) < 1_000_000
            and entry["size"] == len(content)
            and entry["sha256"] == sha256(content).hexdigest()
        ):
            raise ValueError("invalid synthetic JPEG or checksum: " + name)
        encoded[name] = base64.b64encode(content).decode("ascii")
    template = (ROOT / "qa/notebook_material_ui_test.dart.in").read_text()
    marker = "/* SYNTHETIC_JPEGS */"
    if template.count(marker) != 1:
        raise ValueError("test template must contain exactly one fixture marker")
    source = template.replace(marker, "const syntheticJpegs = <String, String>" + json.dumps(encoded) + ";")
    file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_test.dart", prefix="notebook_synthetic_", dir=ROOT / "app/test", delete=False
        ) as temporary:
            file = Path(temporary.name)
            temporary.write(source)
        command = [args.flutter, "test", "--no-pub", "--concurrency=1", "--reporter", "expanded"]
        if args.platform == "chrome":
            command.extend(["--platform", "chrome"])
        command.append(str(file.relative_to(ROOT / "app")))
        subprocess.run(command, cwd=ROOT / "app", check=True)
    finally:
        if file is not None:
            file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
