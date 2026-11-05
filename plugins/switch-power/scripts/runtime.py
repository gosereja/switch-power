#!/usr/bin/env python3
"""Native Codex discovery and local state CLI. Never launches agents."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time

import policy


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('Refusing symlink state file')
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.switch-power-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Store:
    def __init__(self, root=None):
        home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
        self.root = Path(root or os.environ.get('SWITCH_POWER_STATE_DIR', home / 'switch-power/state'))

    def key(self, session):
        if not isinstance(session, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', session):
            raise ValueError('Valid native session id required (CODEX_THREAD_ID or --session)')
        return hashlib.sha256(session.encode()).hexdigest()

    def session_path(self, session):
        return self.root / (self.key(session) + '.json')

    def catalogue_path(self, session):
        return self.root / (self.key(session) + '.catalogue.json')

    def write_catalogue(self, session, value):
        atomic_json(self.catalogue_path(session), value)

    def catalogue(self, session):
        return json.loads(self.catalogue_path(session).read_text())

    @contextmanager
    def session(self, session):
        path = self.session_path(session)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = path.with_suffix('.lock')
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'r+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            if path.is_symlink():
                raise ValueError('Refusing symlink state')
            state = json.loads(path.read_text()) if path.exists() else {}
            if not isinstance(state, dict):
                raise ValueError('Invalid state')
            yield state
            atomic_json(path, state)


class CodexRPC:
    """Bounded stdio client for the supported native app-server protocol."""
    def __init__(self, codex='codex', env=None):
        self.proc = subprocess.Popen([codex, 'app-server', '--stdio'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.proc.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.sequence = 0
        try:
            self.call('initialize', {'clientInfo': {'name': 'switch-power', 'version': '0.1.0'},
                                    'capabilities': {'experimentalApi': True}})
            self.send({'method': 'initialized'})
        except Exception:
            self.close()
            raise

    def send(self, value):
        self.proc.stdin.write(json.dumps(value).encode() + b'\n')
        self.proc.stdin.flush()

    def call(self, method, params, timeout=25):
        self.sequence += 1
        request_id = self.sequence
        self.send({'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if b'\n' not in self.buffer:
                if not self.selector.select(max(0, deadline - time.monotonic())):
                    break
                data = os.read(self.proc.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError('Native Codex app-server exited; inspect codex doctor')
                self.buffer += data
                continue
            line, self.buffer = self.buffer.split(b'\n', 1)
            msg = json.loads(line)
            if msg.get('id') == request_id:
                if 'error' in msg:
                    raise RuntimeError(f'{method}: {msg["error"]}')
                return msg['result']
        raise RuntimeError('Native RPC timeout: ' + method)

    def close(self):
        self.selector.close()
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.proc.stdin.close()
        self.proc.stdout.close()


def fetch_models(codex='codex'):
    rpc = CodexRPC(codex)
    try:
        data, cursor, seen = [], None, set()
        while True:
            page = rpc.call('model/list', {'includeHidden': True, 'limit': 100, 'cursor': cursor})
            data.extend(page['data'])
            cursor = page.get('nextCursor')
            if not cursor:
                return {'data': data, 'fetched_at': time.time()}
            if cursor in seen:
                raise ValueError('Native model/list repeated its pagination cursor')
            seen.add(cursor)
    finally:
        rpc.close()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state-dir')
    p.add_argument('--session', default=os.environ.get('CODEX_THREAD_ID'))
    subs = p.add_subparsers(dest='command', required=True)
    c = subs.add_parser('catalog')
    c.add_argument('--codex', default='codex')
    c.add_argument('--spawn-model', action='append', required=True)
    c.add_argument('--spawn-effort', action='append', required=True)
    t = subs.add_parser('task')
    group = t.add_mutually_exclusive_group(required=True)
    group.add_argument('--new', action='store_true')
    group.add_argument('--continue', dest='continuing', action='store_true')
    t.add_argument('--description')
    s = subs.add_parser('scope')
    s.add_argument('--id', required=True)
    s.add_argument('--description', required=True)
    subs.add_parser('status')
    subs.add_parser('finish')
    for name in ['grant', 'propose', 'failed', 'check']:
        c = subs.add_parser(name)
        c.add_argument('--model', required=True)
        c.add_argument('--effort', required=True)
        if name == 'check':
            c.add_argument('--task-name', required=True)
            c.add_argument('--fork-turns', default='none')
        else:
            c.add_argument('--scope', required=True)
        if name == 'grant':
            c.add_argument('--source', choices=['live_user'], required=True)
            c.add_argument('--turn-id', required=True)
            c.add_argument('--quote', required=True)
        elif name in {'propose', 'failed'}:
            c.add_argument('--reason', required=True)
    r = subs.add_parser('recommend')
    r.add_argument('--kind', choices=['narrow', 'visual', 'code', 'analysis'], required=True)
    r.add_argument('--complexity', type=int, choices=range(5), required=True)
    r.add_argument('--ambiguity', type=int, choices=range(5), required=True)
    r.add_argument('--priority', choices=['balanced', 'quality', 'speed', 'limits'], default='balanced')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    store = Store(args.state_dir)
    try:
        store.key(args.session)
        if args.command == 'catalog':
            value = fetch_models(args.codex)
            value.update(spawn_models=args.spawn_model, spawn_efforts=args.spawn_effort)
            store.write_catalogue(args.session, value)
            result = value
        elif args.command == 'recommend':
            result = policy.recommend(store.catalogue(args.session), args.kind,
                                      args.complexity, args.ambiguity, args.priority)
        else:
            with store.session(args.session) as state:
                if args.command == 'task':
                    if args.new:
                        fresh = policy.new_task(args.description)
                        if state.get('prompt_task_id') is None:
                            fresh.update(prompt=state.get('prompt'), turn_id=state.get('turn_id'),
                                         prompt_task_id=fresh['task_id'])
                        state.clear()
                        state.update(fresh)
                    else:
                        policy.continue_task(state)
                    result = {'task_id': state['task_id'], 'description': state['description']}
                elif args.command == 'scope':
                    result = {'task_name': policy.add_scope(state, args.id, args.description)}
                elif args.command == 'grant':
                    policy.available(store.catalogue(args.session), args.model, args.effort)
                    result = policy.grant(state, args.model, args.effort, args.scope,
                                          args.source, args.turn_id, args.quote)
                elif args.command == 'propose':
                    policy.available(store.catalogue(args.session), args.model, args.effort)
                    result = policy.propose(state, args.model, args.effort, args.scope, args.reason)
                elif args.command == 'failed':
                    policy.mark_failed(state, args.model, args.effort, args.scope, args.reason)
                    result = {'recorded': True}
                elif args.command == 'check':
                    result = policy.check(store.catalogue(args.session), state, args.model,
                                          args.effort, args.task_name, args.fork_turns)
                elif args.command == 'finish':
                    state.clear()
                    result = {'grants_cleared': True}
                else:
                    result = {k: v for k, v in state.items() if k != 'prompt'}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if isinstance(result, dict) and result.get('allowed') is False else 0
    except Exception as exc:
        print(json.dumps({'error': str(exc), 'status': 'not_launched'}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
