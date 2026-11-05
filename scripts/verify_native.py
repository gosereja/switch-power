#!/usr/bin/env python3
"""Read-only native plugin/skill/hook discovery. Creates no Codex chats."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/switch-power'
sys.path.insert(0, str(PLUGIN / 'scripts'))
from runtime import CodexRPC

SELECTOR = 'switch-power@switch-power-personal'


def verify(home, codex='codex', disabled=False):
    env = dict(os.environ, CODEX_HOME=str(home))
    rpc = CodexRPC(codex, env=env)
    try:
        with tempfile.TemporaryDirectory(prefix='switch-power-project-a-') as a, \
             tempfile.TemporaryDirectory(prefix='switch-power-project-b-') as b:
            skills = rpc.call('skills/list', {'cwds': [a, b], 'forceReload': True})
            hooks = rpc.call('hooks/list', {'cwds': [a, b]})
            result = {'native_version': subprocess.check_output([codex, '--version'], env=env, text=True).strip(),
                      'mode': 'disabled' if disabled else 'enabled', 'projects': []}
            for entry, hook_entry in zip(skills['data'], hooks['data']):
                selected = [s for s in entry['skills'] if s.get('pluginId') == SELECTOR and s['enabled']]
                own_hooks = [h for h in hook_entry['hooks'] if h.get('pluginId') == SELECTOR or
                             'switch-power/marketplace/plugins/switch-power/hooks/guard.py' in h.get('command', '')]
                if entry.get('errors') or hook_entry.get('errors'):
                    raise ValueError('Native loader errors: ' + str(entry.get('errors', []) + hook_entry.get('errors', [])))
                if disabled:
                    if selected or own_hooks:
                        raise ValueError('Disabled plugin still supplies skills or hooks')
                elif len(selected) != 1 or len(own_hooks) != 4:
                    raise ValueError('Expected one enabled skill and four native hooks per project')
                result['projects'].append({'skill_names': [s['name'] for s in selected],
                    'skill_scope': [s['scope'] for s in selected],
                    'hooks': [{'event': h['eventName'], 'source': h['source'],
                               'trust': h['trustStatus']} for h in own_hooks],
                    'loader_errors': []})
            files = [Path(home) / 'AGENTS.override.md', Path(home) / 'AGENTS.md']
            effective = next((p for p in files if p.exists() and p.read_text().strip()), None)
            bootstrap = bool(effective and '<!-- switch-power:begin -->' in effective.read_text())
            if bootstrap == disabled:
                raise ValueError('Global bootstrap state does not match requested plugin state')
            result.update(global_bootstrap_present=bootstrap,
                bootstrap_injected_into_model='not_tested_no_new_chat_created',
                actual_hook_interception='not_tested_requires_trusted_hook_and_real_turn',
                backend_model_attestation='not_available_from_discovery')
            return result
    finally:
        rpc.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    p.add_argument('--codex', default='codex')
    p.add_argument('--expect-disabled', action='store_true')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        result = verify(args.codex_home, args.codex, args.expect_disabled)
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded)
        print(encoded, end='')
        return 0
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
