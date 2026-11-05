"""Owned synthetic-family direct update test on a dedicated emulator.

Prepare a lower signed Direct APK and leave its unauthenticated login visible;
dismiss any already-open update dialog first. Deploy a higher Direct release.
This deliberately clears only the dedicated emulator app after deleting the
created synthetic family. Never use it with an existing account or real device.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path
import httpx
import android_smoke as n
import android_update as u
parser=argparse.ArgumentParser()
parser.add_argument('--from-code',type=int,required=True)
parser.add_argument('--to-code',type=int,required=True)
parser.add_argument('--clear-dedicated-emulator-app-data',action='store_true',required=True)
args=parser.parse_args()
assert args.to_code > args.from_code
assert n.adb('shell','getprop','ro.kernel.qemu').strip()==b'1'
n.wait('Willkommen zurück',seconds=10)
private=Path('/tmp/schulpilot-own-update-fixture.json')
if private.exists():
    raise SystemExit('Previous fixture requires cleanup')
screens=[n.ARTIFACTS / 'android-update-system-confirmation.png', n.ARTIFACTS / 'android-updated-current-version.png']
if any(path.exists() for path in screens):
    raise SystemExit('Inspect existing update screenshots before this test')
assert u.installed_code()==args.from_code
report={'synthetic_only': True, 'external_ai_calls': 0, 'cleanup_complete': False}
with httpx.Client(base_url=n.BASE, headers=n.HEADERS, timeout=40) as parent:
    response=parent.post('/demo'); response.raise_for_status(); demo=response.json()
    fd=os.open(private,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: json.dump(demo,f)
    try:
        assert demo['user']['role']=='parent' and all(x['synthetic'] for x in demo['user']['families'])
        creds=demo['credentials']; assert re.fullmatch(r'kind-[a-f0-9]{10}',creds['child_username'])
        parent.headers['Authorization']='Bearer '+demo['token']
        family=parent.get('/families/'+demo['user']['families'][0]['id']); family.raise_for_status()
        profile=next(x for x in family.json()['children'] if x['id']==demo['child_id'])
        name='Updatekind'+creds['child_username'][-6:]
        payload={k:profile[k] for k in ('grade','subjects','school_type','region')}; payload['display_name']=name
        update=parent.put('/children/'+demo['child_id'],json=payload,headers={'If-Match':profile['profile_revision']}); update.raise_for_status()
        before=parent.get('/materials/'+demo['material_id']); before.raise_for_status(); before=before.json()
        assert before['id']==demo['material_id'] and before['synthetic'] and 'content' in before
        sessions_before=parent.get('/children/'+demo['child_id']+'/sessions'); sessions_before.raise_for_status()
        previous_sessions={x['id'] for x in sessions_before.json()}
        n.login(creds['child_username'],creds['child_password'])
        n.wait_any(('Jetzt lernen','Weiterlernen','Freiwillig üben','Heute'),seconds=60)
        n.press('Konto'); n.wait('Abmelden')
        n.adb('shell','input','keyevent','4')
        sessions=parent.get('/children/'+demo['child_id']+'/sessions'); sessions.raise_for_status()
        own_sessions={x['id'] for x in sessions.json()}-previous_sessions
        assert len(own_sessions)==1
        assert u.installed_code()==args.from_code
        report['signed_in_before_update']=True
        p=subprocess.run([sys.executable,'qa/android_update.py','--upgrade'],capture_output=True,text=True,timeout=400)
        if p.returncode: raise RuntimeError('Update driver failed; details intentionally withheld')
        upgrade=json.loads(p.stdout)
        assert upgrade['previous_code']==args.from_code and upgrade['installed_code']==args.to_code and upgrade['system_install_confirmed'] and not upgrade['adb_install_used_for_upgrade']
        n.wait_any(('Jetzt lernen','Weiterlernen','Freiwillig üben','Heute'),seconds=60)
        n.press('Konto'); n.wait('Abmelden')
        sessions=parent.get('/children/'+demo['child_id']+'/sessions'); sessions.raise_for_status()
        assert own_sessions <= {x['id'] for x in sessions.json()}
        report['same_synthetic_child_session_active_after_update']=True
        report['client_session_id_independently_observed']=False
        after=parent.get('/materials/'+demo['material_id']); after.raise_for_status(); after=after.json()
        assert after['id']==before['id'] and after.get('content')==before.get('content')
        report['synthetic_material_unchanged_after_update']=True
        report['material_visible_in_app_before_and_after']=False
        report['upgrade']=upgrade
    finally:
        response=parent.request('DELETE','/account',json={'password':demo['credentials']['parent_password']})
        if response.status_code != 200:
            print(json.dumps({'cleanup_complete':False,'fixture_retained_for_recovery':True}),flush=True)
            raise RuntimeError('Synthetic family cleanup failed')
        private.unlink()
        n.adb('shell','pm','clear',n.PACKAGE)
        for path in screens:
            if path.exists(): path.unlink()
        report['cleanup_complete']=True
        print(json.dumps(report),flush=True)
