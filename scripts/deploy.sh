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
release_stamp="$(python3 scripts/release_timestamp.py)"
release="${release_stamp}-$(git rev-parse --short "$build_commit")"
# Incomplete uploads stay outside the tree traversed by even older prune scripts.
remote_stage="/opt/schulpilot/staging/$release"
lock_token="$(ssh dorfspy python3 - prepare "$release" < deploy/stage_release.py)"
deploy_aborted=true
repair_restart_done=false

cleanup_deployment() {
  if [[ "$deploy_aborted" == true ]]; then
    echo "Deployment failed or aborted; preserving stage and lease for operator inspection..." >&2
    ssh dorfspy python3 - abort "$release" "$lock_token" < deploy/stage_release.py 2>/dev/null || true
  fi
  if [[ "$repair_restart_done" != true ]]; then
    echo "Repair services remain stopped: verify source/schema and restart explicitly after resolving deployment failure." >&2
  fi
}
trap cleanup_deployment EXIT

ssh -o BatchMode=yes dorfspy python3 - < deploy/bootstrap_host.py
rsync -a --chown=root:root --chmod=Dgo-w,Fgo-w --exclude='__pycache__' --exclude='.pytest_cache' backend deploy workers "dorfspy:$remote_stage/"
rsync -a --chown=root:root --chmod=Dgo=rx,Fgo=rX app/build/web/ "dorfspy:$remote_stage/web/"
ssh dorfspy "mkdir -m 755 $remote_stage/downloads"
rsync -a --chown=root:root --chmod=Fgo=rX artifacts/schulpilot-android.apk "dorfspy:$remote_stage/downloads/schulpilot-android.apk"
rsync -a --chown=root:root --chmod=Fgo=rX artifacts/android-release.json "dorfspy:$remote_stage/android-release.json"
rsync -a --no-links artifacts/repair-source.tar.gz "dorfspy:$remote_stage/repair-source.tar.gz"
ssh dorfspy "chown root:schulpilot $remote_stage/repair-source.tar.gz && chmod 640 $remote_stage/repair-source.tar.gz"
ssh dorfspy python3 - staged "$remote_stage" "$release_apk_sha" "$release_proof" "$release_android_sha" "$repair_sha" < scripts/release_attestation.py
ssh dorfspy "chmod 755 $remote_stage/downloads && chmod 644 $remote_stage/downloads/schulpilot-android.apk $remote_stage/android-release.json"
ssh dorfspy python3 - "$release" "$build_commit" <<'PY'
import json,os,sys
from pathlib import Path
root=Path('/opt/schulpilot/staging')/sys.argv[1]
os.umask(0o077)
fd=os.open(root/'release.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as output:
    output.write(json.dumps({'release_id':sys.argv[1],'source_commit':sys.argv[2]})+'\n')
    output.flush()
    os.fchmod(output.fileno(),0o644)
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
ssh dorfspy python3 - staged "$remote_stage" "$release_apk_sha" "$release_proof" "$release_android_sha" "$repair_sha" < scripts/release_attestation.py
ssh dorfspy python3 - publish "$release" "$lock_token" < deploy/stage_release.py
ssh dorfspy python3 - staged "/opt/schulpilot/releases/$release" "$release_apk_sha" "$release_proof" "$release_android_sha" "$repair_sha" < scripts/release_attestation.py
ssh dorfspy "python3 /opt/schulpilot/releases/$release/deploy/activate.py $release --token $lock_token"
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
ssh dorfspy python3 - finish "$release" "$lock_token" < deploy/stage_release.py
deploy_aborted=false
trap - EXIT
if ! ssh -o BatchMode=yes dorfspy sudo -n python3 /opt/schulpilot/current/deploy/prune_releases.py --apply; then
  echo "WARNING: deployment is healthy, but obsolete release cleanup was skipped; inspect the cleanup message above." >&2
fi
