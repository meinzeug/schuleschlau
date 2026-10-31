"""Read-only, two-host backup comparison. This tool cannot authorize deletion.

The remote command only reads metadata and ciphertext and is sent via stdin.
Only the explicitly requested private local manifest is written. Coordination
with backup, restore, deployment, offsite pulls and other operators remains
unresolved; all findings are stale as soon as either host changes.
"""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
NAME = re.compile(r"\d{8}T\d{6}Z\.tar\.enc\Z")

# This constant, not user input, is executed on the backup server. It returns
# metadata and ciphertext hashes only; it never returns archive contents.
REMOTE_SCAN = r'''
import hashlib,json,os,re,stat,time
from pathlib import Path
root=Path('/var/backups/schulpilot')
name_re=re.compile(r'\d{8}T\d{6}Z\.tar\.enc\Z')
def ident(s):
 return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_uid,s.st_nlink,s.st_mode]
def listing():
 return sorted(p.name for p in root.glob('*.tar.enc'))
names=listing()
if not names or any(not name_re.fullmatch(n) for n in names): raise RuntimeError('Invalid inventory')
items=[]
for name in names:
 path=root/name
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as source:
  before=os.fstat(source.fileno())
  if not stat.S_ISREG(before.st_mode) or before.st_uid!=0 or before.st_nlink!=1 or before.st_mode&0o077: raise RuntimeError('Invalid archive metadata')
  digest=hashlib.file_digest(source,'sha256').hexdigest()
  after=os.fstat(source.fileno())
 if ident(before)!=ident(after) or ident(after)!=ident(os.lstat(path)): raise RuntimeError('Archive changed')
 items.append({'name':name,'identity':ident(after),'sha256':digest})
if listing()!=names: raise RuntimeError('Inventory changed')
for item in items:
 if ident(os.lstat(root/item['name']))!=item['identity']: raise RuntimeError('Archive changed')
report=json.loads(Path('/var/backups/schulpilot-monitor/restore-check.json').read_text())
if report.get('authenticated_restore') is not True: raise RuntimeError('Missing authenticated restore')
restore=report.get('backup')
if restore not in names: raise RuntimeError('Missing restore point')
releases=[]
for label in ('current','previous'):
 name=Path('/opt/schulpilot',label).resolve(strict=True).name
 m=re.match(r'^(\d{8}T\d{6}Z)-',name)
 if not m: raise RuntimeError('Invalid release identity')
 releases.append(m.group(1))
print(json.dumps({'archives':items,'restore':restore,'release_stamps':releases,'server_now':int(time.time())}))
'''


def timestamp(name):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Invalid archive identity")
    return int(datetime.strptime(name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp())


def file_identity(st):
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_uid, st.st_nlink, st.st_mode]


def local_digest(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or before.st_mode & 0o077):
            raise ValueError("Untrusted local copy metadata")
        digest = hashlib.file_digest(source, "sha256").hexdigest()
        after = os.fstat(source.fileno())
    if file_identity(before) != file_identity(after) or file_identity(after) != file_identity(os.lstat(path)):
        raise ValueError("Local copy changed")
    return file_identity(after), digest


def remote_scan(host):
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]*", host):
        raise ValueError("Invalid SSH alias")
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, "sudo -n python3 -"],
        input=REMOTE_SCAN, text=True, capture_output=True, check=True, timeout=1800,
    )
    return json.loads(result.stdout)


def build_manifest(inventory, offsite, protected):
    if not isinstance(inventory, dict) or type(inventory.get("server_now")) is not int:
        raise ValueError("Invalid server inventory")
    now = inventory["server_now"]
    records = inventory.get("archives")
    if not isinstance(records, list) or not records:
        raise ValueError("Missing server archives")
    by_name = {}
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Invalid server archive")
        name = row.get("name")
        timestamp(name)
        identity = row.get("identity")
        digest = row.get("sha256")
        if (name in by_name or not isinstance(identity, list) or len(identity) != 8
                or any(type(n) is not int for n in identity)
                or identity[5] != 0 or identity[6] != 1 or not stat.S_ISREG(identity[7])
                or identity[7] & 0o077 or not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            raise ValueError("Invalid server archive metadata")
        by_name[name] = row

    restore = inventory.get("restore")
    protected = set(protected)
    if not protected or restore not in by_name or not protected <= by_name.keys():
        raise ValueError("Restore or deployment protection incomplete")
    releases = inventory.get("release_stamps")
    if not isinstance(releases, list) or len(releases) != 2:
        raise ValueError("Release protection incomplete")
    release_times = [timestamp(stamp + ".tar.enc") for stamp in releases]
    protected.update((restore, max(by_name)))
    protected.update(name for name in by_name if any(abs(timestamp(name) - release) <= 600 for release in release_times))

    slots, name_slot = {}, {}
    for name in by_name:
        age = now - timestamp(name)
        if 2 * DAY <= age < 7 * DAY:
            slot = (6, timestamp(name) // 21600)
        elif 7 * DAY <= age <= 14 * DAY:
            slot = (12, timestamp(name) // 43200)
        else:
            continue
        name_slot[name] = slot
        slots[slot] = max(name, slots.get(slot, name))
    protected.update(slots.values())

    directory = os.lstat(offsite)
    if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid() or directory.st_mode & 0o077):
        raise ValueError("Offsite directory is not private")
    copies = {}
    for name in name_slot:
        try:
            ident, digest = local_digest(offsite / name)
        except (OSError, ValueError):
            continue
        source = by_name[name]
        if ident[2] == source["identity"][2] and digest == source["sha256"]:
            copies[name] = ident
    # Recheck every collected local identity after all potentially long reads.
    for name, ident in list(copies.items()):
        try:
            if file_identity(os.lstat(offsite / name)) != ident:
                del copies[name]
        except OSError:
            del copies[name]
    valid_slots = {slot for slot, name in slots.items() if name in copies
                   and by_name[name]["identity"][3] <= (now - 2 * DAY) * 1_000_000_000}
    selected = []
    for name, slot in sorted(name_slot.items()):
        source = by_name[name]
        # Do not select a recently modified server archive just because its
        # name says it is old. Compare server metadata to server time only.
        if (name not in protected and name in copies and slot in valid_slots
                and source["identity"][3] <= (now - 2 * DAY) * 1_000_000_000):
            selected.append({"name": name, "server_identity": source["identity"],
                             "offsite_identity": copies[name], "sha256": source["sha256"]})
    return {"version": 1, "server_now": now, "advisory_only": True,
            "offsite_independence_and_concurrent_writers_unverified": True,
            "server_inventory": inventory,
            "protected_names": sorted(protected),
            "verified_offsite_identities": copies,
            "slot_survivors": [{"hours": slot[0], "utc_slot": slot[1], "name": name}
                               for slot, name in sorted(slots.items())],
            "candidates": selected}


def write_new_private_manifest(path, manifest):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    # On failure retain a private, possibly incomplete file for operator
    # inspection rather than unlinking a path another process might replace.
    with os.fdopen(fd, "w") as output:
        json.dump(manifest, output, separators=(",", ":"))
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="dorfspy")
    parser.add_argument("--offsite-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--keep", action="append", required=True)
    args = parser.parse_args()
    try:
        inventory = remote_scan(args.host)
        result = build_manifest(inventory, args.offsite_dir, args.keep)
        write_new_private_manifest(args.manifest, result)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        raise SystemExit("Audit failed; no backup was changed.") from None
    print(json.dumps({"advisory_only": True, "candidates": len(result["candidates"]),
                      "bytes": sum(item["server_identity"][2] for item in result["candidates"])}))


if __name__ == "__main__":
    main()
