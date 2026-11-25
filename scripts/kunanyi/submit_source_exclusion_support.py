"""Submit the exposed diagnostic and bounded cohort array from a verified private PBS stage."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def job(job_id):
    rows = json.loads(subprocess.check_output(
        ['/opt/pbs/bin/qstat', '-xf', '-F', 'json', job_id], text=True))['Jobs']
    return rows[job_id]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email-from-job', required=True)
    parser.add_argument('--stage-pin', required=True)
    parser.add_argument('--plan-pin', required=True)
    parser.add_argument('--group', choices=('development', 'cohort'), required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if sha('stage.sha256') != args.stage_pin or sha('plan.json') != args.plan_pin:
        raise ValueError('stage or plan digest differs')
    subprocess.run(['sha256sum', '--check', '--quiet', 'stage.sha256'], check=True)
    predecessor = job(args.email_from_job)
    email = predecessor['Mail_Users']
    if (set(predecessor['Mail_Points']) != set('ae') or not re.fullmatch(r'[^@\s,]+@[^@\s,]+', email)
            or predecessor['Job_Owner'].split('@')[0] != os.environ['USER']):
        raise ValueError('previous completion/abort email route could not be verified')
    registry = Path('submissions')
    registry.mkdir(exist_ok=True)
    stage_flags = f'SOURCE_STAGE_SHA256={args.stage_pin},SOURCE_PLAN_SHA256={args.plan_pin}'
    groups = ([('development', None)] if args.group == 'development' else
              [('cohort-' + r, r) for r in ('1-6', '7-12', '13-16', '17-22')])
    previous = None
    for name, indices in groups:
        out = registry / (name + '.json')
        if out.exists():
            record = json.loads(out.read_text())
            if (record['plan_sha256'], record['stage_sha256']) != (args.plan_pin, args.stage_pin):
                raise ValueError('existing submission has a different source or plan')
            jid = record['job_id']
        else:
            if indices is None:
                argv = ['-N', 'srcx_ghi20', '-r', 'n', '-v', stage_flags + ',SOURCE_SLOT=0']
            else:
                argv = ['-N', 'srcx_' + indices.replace('-', '_'), '-r', 'y', '-J', indices, '-v', stage_flags]
                if previous:
                    argv.extend(['-W', 'depend=afterany:' + previous])
            submission = subprocess.run(['/opt/pbs/bin/qsub', '-m', 'ae', '-M', email,
                                         *argv, 'source_exclusion_support.pbs'], text=True, capture_output=True)
            if submission.returncode:
                raise RuntimeError('PBS refused the projection submission: ' + submission.stderr.strip().replace(email, '[recipient]'))
            jid = submission.stdout.strip()
            record = {'job_id': jid, 'group': name, 'stage_sha256': args.stage_pin,
                      'plan_sha256': args.plan_pin, 'indices': indices, 'afterany': previous}
            with out.open('x') as stream:
                stream.write(json.dumps(record, sort_keys=True) + '\n')
        submitted = job(jid)
        if (set(submitted['Mail_Points']) != set('ae') or submitted['Mail_Users'] != email
                or submitted.get('array_indices_submitted') != indices):
            raise ValueError(f'PBS recorded different notification settings or array indices for {jid}')
        print(jid, submitted['job_state'], 'completion and abort email verified', flush=True)
        previous = jid


if __name__ == '__main__':
    main()
