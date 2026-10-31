#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f app/build/web/index.html
test -f artifacts/schulpilot-android.apk
test -f artifacts/repair-source.tar.gz
build_commit="$(git rev-parse HEAD)"
repair_binding="$(python3 scripts/prepare_repair_source.py --commit "$build_commit" --output artifacts/repair-source.tar.gz --verify)"
python3 scripts/android_manifest.py
release_binding="$(python3 scripts/release_attestation.py verify)"
read -r release_apk_sha release_proof release_android_sha <<< "$release_binding"
repair_sha="$(printf '%s' "$repair_binding" | python3 scripts/release_attestation.py bind-repair "$release_proof" "$build_commit")"
release="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short "$build_commit")"
ssh -o BatchMode=yes dorfspy python3 - < deploy/bootstrap_host.py
# Incomplete uploads stay outside the tree traversed by even older prune scripts.
# This is not a deployment lock: publication/activation still need coordination.
remote_stage="/opt/schulpilot/staging/$release"
ssh dorfspy python3 - prepare "$release" < deploy/stage_release.py
rsync -a --chown=root:root --chmod=Dgo-w,Fgo-w --exclude='__pycache__' --exclude='.pytest_cache' backend deploy workers "dorfspy:$remote_stage/"
rsync -a app/build/web/ "dorfspy:$remote_stage/web/"
ssh dorfspy "mkdir -p $remote_stage/downloads"
rsync -a artifacts/schulpilot-android.apk "dorfspy:$remote_stage/downloads/schulpilot-android.apk"
rsync -a artifacts/android-release.json "dorfspy:$remote_stage/android-release.json"
rsync -a --no-links artifacts/repair-source.tar.gz "dorfspy:$remote_stage/repair-source.tar.gz"
ssh dorfspy "chown root:schulpilot $remote_stage/repair-source.tar.gz && chmod 640 $remote_stage/repair-source.tar.gz"
ssh dorfspy python3 - staged "$remote_stage" "$release_apk_sha" "$release_proof" "$release_android_sha" "$repair_sha" < scripts/release_attestation.py
ssh dorfspy "chmod 755 $remote_stage/downloads && chmod 644 $remote_stage/downloads/schulpilot-android.apk $remote_stage/android-release.json"
ssh dorfspy python3 - "$release" "$build_commit" <<'PY'
import json,sys
from pathlib import Path
root=Path('/opt/schulpilot/staging')/sys.argv[1]
(root/'release.json').write_text(json.dumps({'release_id':sys.argv[1],'source_commit':sys.argv[2]})+'\n')
PY
# Preserve explicit operator activation; never auto-install/enable repair services.
# A failed activation leaves them stopped, including after rollback. The operator
# must verify old schema/source compatibility before an explicit restart.
repair_state_encoded="$(ssh dorfspy python3 - <<'PY'
import base64,json,subprocess
from pathlib import Path
names=('schulpilot-repair.service','schulpilot-repair-dispatcher.service')
state={name:Path('/etc/systemd/system',name).is_file() and subprocess.run(['systemctl','is-active','--quiet',name]).returncode==0 for name in names}
installed=[name for name in names if Path('/etc/systemd/system',name).is_file()]
if installed:
    subprocess.run(['systemctl','stop',*reversed(installed)],check=True)
# ssh joins remote argv into shell text: transport only shell-safe ASCII.
print(base64.b64encode(json.dumps(state,separators=(',',':')).encode()).decode('ascii'))
PY
)"
repair_restart_done=false
trap 'if [[ "$repair_restart_done" != true ]]; then echo "Repair services remain stopped: verify source/schema and restart explicitly after resolving deployment failure." >&2; fi' EXIT
ssh dorfspy python3 - staged "$remote_stage" "$release_apk_sha" "$release_proof" "$release_android_sha" "$repair_sha" < scripts/release_attestation.py
ssh dorfspy python3 - publish "$release" < deploy/stage_release.py
ssh dorfspy python3 - staged "/opt/schulpilot/releases/$release" "$release_apk_sha" "$release_proof" "$release_android_sha" "$repair_sha" < scripts/release_attestation.py
ssh dorfspy "python3 /opt/schulpilot/releases/$release/deploy/activate.py $release"
ssh dorfspy "if test -f /etc/systemd/system/schulpilot-codex.service; then python3 /opt/schulpilot/releases/$release/deploy/install_codex.py; fi"
curl --retry 10 --retry-all-errors --retry-delay 3 --fail --silent --show-error https://schulpilot.dorfspy.de/api/health
ssh dorfspy python3 - "$release" "$repair_state_encoded" <<'PY'
import base64,binascii,json,shutil,subprocess,sys
from pathlib import Path
root=Path('/opt/schulpilot/releases')/sys.argv[1]
if Path('/opt/schulpilot/current').resolve()!=root.resolve():
    raise SystemExit('Repair restart refused: active source differs from deployed release.')
try:
    encoded=sys.argv[2]
    if len(encoded)>512:
        raise ValueError('state size')
    state=json.loads(base64.b64decode(encoded,validate=True))
    names={'schulpilot-repair.service','schulpilot-repair-dispatcher.service'}
    if not isinstance(state,dict) or set(state)!=names or any(type(value) is not bool for value in state.values()):
        raise ValueError('state flags')
except (IndexError,ValueError,TypeError,binascii.Error):
    raise SystemExit('Repair restart refused: invalid service state.') from None
name='schulpilot-repair-dispatcher.service'
if Path('/etc/systemd/system',name).is_file():
    shutil.copy2(root/'deploy'/name,Path('/etc/systemd/system')/name)
    subprocess.run(['systemctl','daemon-reload'],check=True)
for name in ('schulpilot-repair.service','schulpilot-repair-dispatcher.service'):
    if state.get(name) is True:
        subprocess.run(['systemctl','start',name],check=True)
PY
repair_restart_done=true
trap - EXIT
if ! ssh -o BatchMode=yes dorfspy sudo -n python3 /opt/schulpilot/current/deploy/prune_releases.py --apply; then
  echo "WARNING: deployment is healthy, but obsolete release cleanup was skipped; inspect the cleanup message above." >&2
fi
