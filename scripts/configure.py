#!/usr/bin/env python3
"""Coordinator model defaults: separate from the plugin and reversible."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import tomllib

from config_edit import set_value, write_text

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/switch-power'
if not PLUGIN.exists():
    PLUGIN = ROOT / 'marketplace/plugins/switch-power'
sys.path.insert(0, str(PLUGIN / 'scripts'))
from runtime import fetch_models
import policy


def apply(home, model, effort):
    home = Path(home)
    path = home / 'config.toml'
    original = path.read_text() if path.exists() else ''
    parsed = tomllib.loads(original)
    marker = home / 'switch-power/coordinator-backup.json'
    if marker.exists():
        saved = json.loads(marker.read_text())
        if all(parsed.get(k) == v for k, v in saved['applied'].items()):
            saved['applied'] = {'model': model, 'model_reasoning_effort': effort}
        else:
            raise ValueError('Coordinator settings changed since prior apply; restore or review backup first')
    else:
        saved = {'original': {k: {'present': k in parsed, 'value': parsed.get(k)}
                  for k in ['model', 'model_reasoning_effort']},
                 'applied': {'model': model, 'model_reasoning_effort': effort}}
    updated = set_value(original, (), 'model', model)
    updated = set_value(updated, (), 'model_reasoning_effort', effort)
    write_text(marker, json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
    write_text(path, updated)
    return saved['applied']


def restore(home):
    home = Path(home)
    marker = home / 'switch-power/coordinator-backup.json'
    saved = json.loads(marker.read_text())
    path = home / 'config.toml'
    text = path.read_text()
    parsed = tomllib.loads(text)
    if any(parsed.get(k) != v for k, v in saved['applied'].items()):
        raise ValueError('Refusing to overwrite later user changes to coordinator settings')
    for k, record in saved['original'].items():
        text = set_value(text, (), k, record['value'], remove=not record['present'])
    write_text(path, text)
    marker.unlink()
    return {'restored': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    p.add_argument('--codex', default='codex')
    p.add_argument('action', choices=['inspect', 'apply', 'upgrade', 'restore'])
    a = p.parse_args()
    try:
        if a.action == 'restore':
            result = restore(a.codex_home)
        else:
            os.environ['CODEX_HOME'] = str(a.codex_home)
            c = fetch_models(a.codex)
            current = tomllib.loads((a.codex_home / 'config.toml').read_text()).get('model') if (a.codex_home / 'config.toml').exists() else None
            if a.action == 'apply':
                # This exact initial ID was verified against native model/list.
                target = 'gpt-6.1-sol'
            elif a.action == 'upgrade':
                target = policy.upgrade(c, current)
                if target is None:
                    print(json.dumps({'changed': False, 'current': current,
                        'reason': 'Native catalogue supplies no verified Sol upgrade target'}, ensure_ascii=False))
                    return 0
            else:
                target = current
            row = next((r for r in c['data'] if r['model'] == target), None)
            if not row or 'high' not in {e['reasoningEffort'] for e in row['supportedReasoningEfforts']}:
                raise ValueError('Requested coordinator is unavailable or lacks high; no settings changed')
            result = {'catalogue_verified': target, 'effort': 'high',
                      'next_verified_sol': policy.upgrade(c, target),
                      'note': 'New sessions may have project/profile/managed overrides'}
            if a.action != 'inspect':
                result.update(apply(a.codex_home, target, 'high'))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
