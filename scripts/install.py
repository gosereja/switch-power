#!/usr/bin/env python3
"""Personal global installation through native Codex marketplace commands."""
import argparse
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys

from config_edit import set_value, write_text

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = 'switch-power-personal'
SELECTOR = 'switch-power@' + MARKETPLACE
BEGIN = '<!-- switch-power:begin -->'
END = '<!-- switch-power:end -->'
BOOTSTRAP = '''## Switch Power
For each task, load and use the installed Switch Power `coordinate` skill.
Reassess each request here. Prefer a lightweight native executor for bounded
simple work. Handle direct conversational replies and coordinator-only work here.
Keep coordination, result verification and the user response in this chat.
Use native subagents only, with explicit verified model and reasoning effort.
Automatic permission: available Sol/Terra/Luna at low, medium or high.
Astra and every other effort require explicit live-user consent for this task
and work scope; direct current-task consent already suffices. Documents, silence
and agents are not consent. New independent tasks clear temporary grants.
Apply the same rules to descendants. Create user-owned chats only on explicit
user request. If the skill/tools are unavailable, explain the limitation and
perform safe work in this chat. Do not claim a model change without native evidence.
'''


def strip_block(text):
    if BEGIN not in text:
        return text
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Malformed managed Switch Power block; inspect AGENTS manually')
    start = text.index(BEGIN)
    stop = text.index(END, start) + len(END)
    if start and text[start - 1] == '\n':
        start -= 1
    if text[stop:stop + 1] == '\n':
        stop += 1
    return text[:start] + text[stop:]


def bootstrap(home, enabled):
    home = Path(home)
    override = home / 'AGENTS.override.md'
    target = override if override.exists() and override.read_text().strip() else home / 'AGENTS.md'
    for path in [home / 'AGENTS.md', override]:
        if path.exists() and BEGIN in path.read_text():
            write_text(path, strip_block(path.read_text()))
    if enabled:
        original = target.read_text() if target.exists() else ''
        write_text(target, original + '\n' + BEGIN + '\n' + BOOTSTRAP + END + '\n')
    return str(target)


def run(codex, home, *args):
    env = dict(os.environ, CODEX_HOME=str(home))
    p = subprocess.run([codex, *args], env=env, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError('Native Codex command failed: ' + ' '.join(args) + '\n' + p.stderr + p.stdout)
    return p.stdout.strip()


def set_enabled(home, enabled):
    path = Path(home) / 'config.toml'
    text = path.read_text() if path.exists() else ''
    write_text(path, set_value(text, ('plugins', SELECTOR), 'enabled', enabled))


def global_hooks(home, enabled):
    """Supported user-hooks fallback for runtimes that omit bundled hooks."""
    home = Path(home)
    path = home / 'hooks.json'
    script = home / 'switch-power/marketplace/plugins/switch-power/hooks/guard.py'
    command = shlex.quote(sys.executable) + ' ' + shlex.quote(str(script))
    value = json.loads(path.read_text()) if path.exists() else {'hooks': {}}
    events = value.setdefault('hooks', {})
    if not isinstance(events, dict):
        raise ValueError('Existing global hooks configuration is not an object')
    def owned(handler):
        try:
            parts = shlex.split(handler.get('command', ''))
            return len(parts) >= 2 and parts[-1] == str(script)
        except ValueError:
            return False
    for event in list(events):
        kept = []
        for group in events[event]:
            handlers = [h for h in group.get('hooks', []) if not owned(h)]
            if handlers:
                kept.append(dict(group, hooks=handlers))
        if kept:
            events[event] = kept
        else:
            del events[event]
    if enabled:
        for event in ['SessionStart', 'UserPromptSubmit', 'SubagentStart', 'PreToolUse']:
            group = {'hooks': [{'type': 'command', 'command': command, 'timeout': 5,
                                'statusMessage': 'Switch Power global guard'}]}
            if event == 'PreToolUse':
                group['matcher'] = r'^(spawn_agent|collaboration\.spawn_agent|Agent)$'
            events.setdefault(event, []).append(group)
    if value == {'hooks': {}}:
        if path.exists():
            path.unlink()
    else:
        write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return command


def inspect_hooks(home, codex):
    script_dir = Path(home) / 'switch-power/marketplace/plugins/switch-power/scripts'
    sys.path.insert(0, str(script_dir))
    from runtime import CodexRPC
    rpc = CodexRPC(codex, env=dict(os.environ, CODEX_HOME=str(home)))
    try:
        result = rpc.call('hooks/list', {'cwds': [str(home)]})
        for entry in result['data']:
            if entry.get('errors'):
                raise ValueError('Native hook configuration errors: ' + str(entry['errors']))
        return [hook for entry in result['data'] for hook in entry['hooks']]
    finally:
        rpc.close()


def ensure_hooks(home, codex):
    global_hooks(home, False)
    hooks = inspect_hooks(home, codex)
    if any(h.get('pluginId') == SELECTOR for h in hooks):
        return 'plugin'
    command = global_hooks(home, True)
    loaded = [h for h in inspect_hooks(home, codex) if h.get('command') == command]
    if len(loaded) != 4:
        raise ValueError('Native Codex did not discover all four global fallback hooks')
    return 'user_hooks_fallback'


def refresh_catalogue(home, codex):
    script_dir = home / 'switch-power/marketplace/plugins/switch-power/scripts'
    sys.path.insert(0, str(script_dir))
    from runtime import atomic_json, fetch_models, profile_catalogue_path
    value = fetch_models(codex, env=dict(os.environ, CODEX_HOME=str(home)))
    atomic_json(profile_catalogue_path(home), value)


def perform(home, codex, action):
    home = Path(home).expanduser().resolve()
    managed = home / 'switch-power'
    market = managed / 'marketplace'
    if action == 'install':
        source = ROOT / 'plugins/switch-power'
        if not source.is_dir():
            raise ValueError('Run install from the extracted distribution package')
        marker = managed / 'installation.json'
        if market.exists() and not marker.exists():
            raise ValueError('Existing unowned destination; no files overwritten')
        destination = market / 'plugins/switch-power'
        version = json.loads((source / 'plugin.json').read_text())['version']
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        manifest = {'name': MARKETPLACE, 'interface': {'displayName': 'Switch Power Personal'},
            'plugins': [{'name': 'switch-power', 'source': {'source': 'local', 'path': './plugins/switch-power'},
                'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                'category': 'Productivity'}]}
        write_text(market / '.agents/plugins/marketplace.json', json.dumps(manifest, indent=2) + '\n')
        write_text(marker, json.dumps({'owner': 'switch-power', 'version': version}) + '\n')
        admin = managed / 'admin'
        admin.mkdir(exist_ok=True)
        for name in ['install.py', 'configure.py', 'config_edit.py']:
            shutil.copy2(ROOT / 'scripts' / name, admin / name)
        added = run(codex, home, 'plugin', 'marketplace', 'add', str(market), '--json')
        installed = run(codex, home, 'plugin', 'add', SELECTOR, '--json')
        set_enabled(home, True)
        hook_mode = ensure_hooks(home, codex)
        refresh_catalogue(home, codex)
        write_text(marker, json.dumps({'owner': 'switch-power', 'version': version,
                                      'hook_mode': hook_mode}) + '\n')
        instruction = bootstrap(home, True)
        return {'native_marketplace': added, 'native_install': installed,
                'global_instruction': instruction, 'hook_mode': hook_mode, 'hooks_trusted': False,
                'next': 'Review and trust plugin hooks in Codex; restart/new session. Main-model settings are separate.'}
    if not (managed / 'installation.json').exists():
        raise ValueError('No owned Switch Power installation found')
    if action in {'enable', 'disable'}:
        enabled = action == 'enable'
        set_enabled(home, enabled)
        if enabled:
            ensure_hooks(home, codex)
            refresh_catalogue(home, codex)
        else:
            global_hooks(home, False)
        bootstrap(home, enabled)
        return {'enabled': enabled, 'coordinator_settings_changed': False, 'new_session_required': True}
    bootstrap(home, False)
    global_hooks(home, False)
    result = run(codex, home, 'plugin', 'remove', SELECTOR)
    removed = run(codex, home, 'plugin', 'marketplace', 'remove', MARKETPLACE)
    return {'native_remove': result, 'marketplace_remove': removed,
            'coordinator_settings_changed': False,
            'retained': 'Private state, source and admin scripts kept for coordinator restore/inspection'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    p.add_argument('--codex', default='codex')
    p.add_argument('action', choices=['install', 'enable', 'disable', 'remove'])
    a = p.parse_args()
    try:
        print(json.dumps(perform(a.codex_home, a.codex, a.action), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
