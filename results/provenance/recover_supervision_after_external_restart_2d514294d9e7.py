"""Restore supervision after the human-approved external checkpoint restart.

This operational helper never launches an incident worker or changes a recipe.
The external restarter owns that recovery; this restores its sleep inhibitor
and the existing frozen Track 4 supervisor after its new identity is verified.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
JOURNAL = Path('/Users/danielfoojunwei/Desktop/liquid probe/work/honest_trait_search_v3/resource_sessions/factorial_native_screen_002_checkpoint_restart_execution.json')
STATUS = Path('results/external_supervision_recovery.json')
lock = open('results/external_supervision_recovery.lock', 'a+')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)


def save(**values):
    temporary = STATUS.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({'helper_pid': os.getpid(), **values}, indent=2) + '\n')
    temporary.replace(STATUS)


def process(pid):
    p = subprocess.run(['ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


try:
    save(status='waiting_for_external_checkpoint_restart', journal=str(JOURNAL))
    while True:
        restart = json.loads(JOURNAL.read_text())
        if restart['status'] == 'restarted':
            pid = restart['restarted_queue_pid']
            expected = ' '.join(restart['plan']['queue_argv'])
            assert process(pid) == expected, 'Restarted queue identity differs'
            current = json.loads(Path('results/incident_queue_status.json').read_text())
            if current['queue_pid'] == pid:
                break
        elif restart['status'] != 'waiting_for_personality_exit':
            raise RuntimeError('External recovery needs inspection: ' + restart['status'])
        time.sleep(5)

    from run_swarm_track4 import verify
    verify()
    for name in ('incident_queue_manifest.json', 'swarm_track4_manifest.json'):
        for filename, digest in json.loads(Path('results', name).read_text())['inputs'].items():
            assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest
    assert process(pid) == expected
    inhibitor = subprocess.Popen(['/usr/bin/caffeinate', '-i', '-w', str(pid)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True, close_fds=True)
    swarm = json.loads(Path('results/swarm_track4_status.json').read_text())
    swarm_pid = swarm['queue_pid']
    if not process(swarm_pid):
        with open('results/swarm_track4_queue.log', 'a') as log:
            child = subprocess.Popen([str(ROOT / '.venv/bin/python'), '-u',
                swarm['runtime_launcher'], *swarm['runtime_arguments']], cwd=ROOT,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, close_fds=True)
        swarm_pid = child.pid
    monitor_path = Path('results/completion_monitor.json')
    monitor = json.loads(monitor_path.read_text())
    monitor.update(incident_queue_pid=pid, idle_sleep_inhibitor_pid=inhibitor.pid,
        swarm_extension_queue_pid=swarm_pid,
        incident_execution_state='External approved checkpoint restart complete; frozen launcher restoring saved phases')
    monitor_path.write_text(json.dumps(monitor, indent=2) + '\n')
    save(status='supervision_restored', incident_queue_pid=pid,
         incident_inhibitor_pid=inhibitor.pid, swarm_supervisor_pid=swarm_pid)
except BaseException as error:
    save(status='failed', error=repr(error), journal=str(JOURNAL))
    raise
