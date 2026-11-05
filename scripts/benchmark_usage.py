#!/usr/bin/env python3
"""Compare live Sol/high runs in isolated Codex profiles. Uses your Codex quota."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/switch-power/scripts'))
from runtime import resolve_codex

MODEL = 'gpt-6.1-sol'
TASKS = {
    'lookup': ('Read service.toml and return only the configured port number.', '9347'),
    'inventory': ('Count Python files under src recursively and return only their count.', '3'),
    'compare': ('Independently check the pending totals in north.csv and south.csv. '
                'Return just the combined total of the amounts for pending rows.', '84'),
}
RECORDER = """import json, sys
from pathlib import Path
event = json.load(sys.stdin)
fields = ('hook_event_name', 'agent_id', 'turn_id', 'model', 'token_usage', 'status')
with Path(sys.argv[1]).open('a', encoding='utf-8') as stream:
    stream.write(json.dumps({key: event.get(key) for key in fields}) + '\\n')
"""


def records(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def create_fixture(path):
    files = {
        'service.toml': '[http]\nport = 9347\n',
        'src/main.py': '# entry point\n', 'src/lib/a.py': '# a\n',
        'src/lib/b.py': '# b\n', 'src/lib/readme.txt': 'text\n',
        'north.csv': 'state,amount\npending,22\ncomplete,80\npending,13\n',
        'south.csv': 'state,amount\npending,49\ncomplete,41\n',
    }
    for name, contents in files.items():
        file = path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(contents, encoding='utf-8')


def configure_recorder(home, recorder, events):
    path = home / 'hooks.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'hooks': {}}
    if os.name == 'nt':
        command = subprocess.list2cmdline([sys.executable, str(recorder), str(events)])
    else:
        command = shlex.join([sys.executable, str(recorder), str(events)])
    for name in ('PostModelRequest', 'SubagentStart', 'SubagentStop'):
        config['hooks'].setdefault(name, []).append({'hooks': [
            {'type': 'command', 'command': command, 'timeout': 5}]})
    path.write_text(json.dumps(config), encoding='utf-8')


def run(codex, home, project, events, mode, case, repeat):
    events.unlink(missing_ok=True)
    prompt, expected = TASKS[case]
    env = dict(os.environ, CODEX_HOME=str(home))
    env.pop('CODEX_THREAD_ID', None)
    env.pop('SWITCH_POWER_STATE_DIR', None)
    start = time.monotonic()
    if mode == 'baseline':
        agent_flags = ['--disable', 'multi_agent', '--disable', 'multi_agent_v2', '-c',
                       'developer_instructions="Complete this task yourself. Do not launch or use '
                       'any subagent, delegate work, or start another Codex session."']
    else:
        agent_flags = ['--enable', 'multi_agent_v2']
    command = [codex, 'exec', '--dangerously-bypass-hook-trust',
               *agent_flags, '--ephemeral', '--json',
               '--skip-git-repo-check', '-C', str(project), '-m', MODEL,
               '-c', 'model_reasoning_effort="high"', '-c', 'approval_policy="never"',
               '-s', 'workspace-write', prompt]
    try:
        p = subprocess.run(command, env=env, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=150)
    except subprocess.TimeoutExpired:
        return {'case': case, 'repeat': repeat, 'mode': mode,
                'seconds': round(time.monotonic() - start, 2), 'correct': False,
                'complete_usage': False, 'error': 'Codex timed out'}
    elapsed = round(time.monotonic() - start, 2)
    stream = [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
    messages = [e['item']['text'] for e in stream if e['type'] == 'item.completed'
                and e['item']['type'] == 'agent_message']
    completed = [e['usage'] for e in stream if e['type'] == 'turn.completed']
    observed = records(events)
    attempts = [e for e in observed if e['hook_event_name'] == 'PostModelRequest']
    counters = ('input_tokens', 'cached_input_tokens', 'output_tokens',
                'reasoning_output_tokens', 'total_tokens')
    counts = {}
    for attempt in attempts:
        model, usage = attempt['model'], attempt['token_usage']
        if model and usage is not None:
            row = counts.setdefault(model, dict.fromkeys(counters, 0))
            for key in counters:
                row[key] += usage[key]
    parents = [a for a in attempts if not a['agent_id']]
    launched = {(e['agent_id'], e['turn_id']) for e in observed
                if e['hook_event_name'] == 'SubagentStart'}
    stopped = {(e['agent_id'], e['turn_id']) for e in observed
               if e['hook_event_name'] == 'SubagentStop'}
    workers = {(a['agent_id'], a['turn_id']) for a in attempts if a['agent_id']}
    has_counts = bool(parents) and all(a['model'] and a['token_usage'] for a in attempts)
    checks = {
        'attempt_usage_present': has_counts,
        'worker_lifecycle_matches': launched == stopped == workers,
        'coordinator_model_matches': bool(parents) and all(a['model'] == MODEL for a in parents),
        'cli_coordinator_totals_match': len(completed) == 1 and has_counts and all(
            sum(a['token_usage'][key] for a in parents) == completed[0][key]
            for key in counters if key != 'total_tokens'),
        'baseline_is_solo': mode != 'baseline' or not workers,
    }
    return {'case': case, 'repeat': repeat, 'mode': mode, 'seconds': elapsed,
            'correct': p.returncode == 0 and bool(messages) and messages[-1].strip() == expected,
            'complete_usage': all(checks.values()), 'checks': checks, 'native_workers': len(launched),
            'worker_models': sorted({a['model'] or 'unknown' for a in attempts if a['agent_id']}),
            'usage_by_model': counts, 'exit_code': p.returncode}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--auth-file', type=Path, default=Path.home() / '.codex/auth.json')
    parser.add_argument('--repeats', type=int, default=2)
    parser.add_argument('--case', choices=TASKS, help='Run one fixture task')
    parser.add_argument('--mode', choices=('baseline', 'plugin'), help='Run one side of a comparison')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 1 or not args.auth_file.is_file():
        parser.error('A positive repeat count and an existing Codex auth file are required')
    codex = resolve_codex(args.codex)
    with tempfile.TemporaryDirectory(prefix='switch-power-benchmark-') as tmp:
        base = Path(tmp).resolve()
        project = base / 'fixture'
        create_fixture(project)
        recorder, events = base / 'record.py', base / 'events.jsonl'
        recorder.write_text(RECORDER, encoding='utf-8')
        homes = {}
        selected_modes = (args.mode,) if args.mode else ('baseline', 'plugin')
        for mode in selected_modes:
            home = base / mode
            home.mkdir(mode=0o700)
            auth = home / 'auth.json'
            auth.write_bytes(args.auth_file.read_bytes())
            auth.chmod(0o600)
            if mode == 'plugin':
                subprocess.run([sys.executable, str(ROOT / 'scripts/install.py'), '--codex-home',
                                str(home), '--codex', codex, 'install'], check=True,
                               stdout=subprocess.DEVNULL, timeout=90)
            configure_recorder(home, recorder, events)
            homes[mode] = home
        with args.output.open('x', encoding='utf-8') as output:
            for repeat in range(1, args.repeats + 1):
                for case in (args.case,) if args.case else TASKS:
                    modes = selected_modes if repeat % 2 else selected_modes[::-1]
                    for mode in modes:
                        row = run(codex, homes[mode], project, events, mode, case, repeat)
                        print(json.dumps(row), file=output, flush=True)
                        print(case, repeat, mode, row['correct'], row['complete_usage'], flush=True)


if __name__ == '__main__':
    main()
