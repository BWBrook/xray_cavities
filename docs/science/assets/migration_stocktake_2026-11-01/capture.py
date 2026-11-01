import json,hashlib,os,subprocess,time,tarfile
from pathlib import Path
base=Path('/u/bwbrook/codex_kunanyi')
out=base/'stocktake_2026-11-01_0453_r2'
out.mkdir(exist_ok=False)
m=base/'scratch_home_migration_2026-10-16'
def snapshot(p):
 b=p.read_bytes();q=out/'migration'/p.relative_to(m);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);return b
plan=json.loads(snapshot(m/'migration_plan.json'))
ph=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
report={'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'plan_hash':ph,'payloads_rehashed':False,'units':[]}
for i,u in enumerate(plan['units']):
 uid=hashlib.sha256((u['source']+'\0'+u['destination']).encode()).hexdigest()[:20];d=m/'state'/('unit-'+uid)
 files={p.name:snapshot(p) for p in d.glob('*') if p.is_file() and p.name in ['manifest.json','status.json','ledger.jsonl','events.jsonl','metadata-policy-receipt.json']}
 status=json.loads(files.get('status.json',b'{"stage":"new"}'));manifest=json.loads(files.get('manifest.json',b'{"entries":{}}'));records=[];partial=0
 for line in files.get('ledger.jsonl',b'').splitlines():
  try:records.append(json.loads(line))
  except json.JSONDecodeError:partial+=1
 verified={r['path']:r for r in records if r.get('event')=='file_verified' and (i!=8 or r.get('verification_epoch')=='c-hi-device-rebind-20261031')}
 src=Path(u['source']);dst=Path(u['destination']);tomb=src.with_name('.'+src.name+'.xray-migration-'+uid+'.tombstone')
 entries=manifest.get('entries',{});regular={k:v for k,v in entries.items() if v['kind']=='file'}
 row={'index':i,'unit_id':uid,**u,'status':status,'source_symlink':src.is_symlink(),'source_exists':src.exists(),'link_target':os.readlink(src) if src.is_symlink() else None,'destination_live_directory':dst.is_dir() and not dst.is_symlink(),'tombstone_exists':os.path.lexists(tomb),'manifest_regular_files':len(regular),'manifest_bytes':sum(v['signature']['size'] for v in regular.values()),'verified_files':len(verified),'verified_bytes':sum(regular[k]['signature']['size'] for k in verified if k in regular),'partial_ledger_lines':partial,'receipt_hash_fields_complete':all(len(r.get('sha256',''))==64 for r in verified.values())}
 report['units'].append(row)
for p in [m/'state/plan-binding.json',m/'state/verified-manifest.json',m/'state/events.jsonl',m/'device_transition_20261031/transition-receipt.json']:
 if p.exists():snapshot(p)
for job in ['870323','870374','870719','870640']:
 r=subprocess.run(['qstat','-xf',job],capture_output=True,text=True);(out/(job+'.qstat.txt')).write_text(r.stdout+r.stderr)
for name in ['migration.device-transition.out','migration.device-transition.err']:
 p=m/name
 if p.exists():(out/name).write_bytes(p.read_bytes()[-18000:])
q=base/'q032_retained_method_ladder_2026-10-31_r1'
for name in ['q032_retained_method_ladder_receipt.json','output_validation.json','stage_checksums.sha256','input_binding_before.json','input_binding_after.json','run.out','run.err']:
 p=q/name
 if p.exists():(out/name).write_bytes(p.read_bytes())
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
archive=out.with_suffix('.tar.gz')
with tarfile.open(archive,'x:gz') as t:t.add(out,arcname=out.name)
print('CAPTURE',archive,archive.stat().st_size,hashlib.sha256(archive.read_bytes()).hexdigest())
for r in report['units']:print(r['index'],r['status']['stage'],r['verified_files'],r['verified_bytes'],r['manifest_bytes'],r['source_symlink'],r['destination_live_directory'],r['tombstone_exists'])
