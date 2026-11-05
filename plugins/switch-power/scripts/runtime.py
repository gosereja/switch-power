#!/usr/bin/env python3
"""Native Codex discovery and local state CLI. Never launches agents."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, suppress
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import queue
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time

import policy
import usage

if os.name == 'nt':
    import msvcrt
else:
    import fcntl


def resolve_codex(codex='codex'):
    if os.name != 'nt':
        return codex
    configured = os.environ.get('CODEX_CLI_PATH') if codex == 'codex' else None
    requested = configured or codex
    located = shutil.which(requested)
    if located and Path(located).suffix.lower() == '.exe':
        return located
    if requested == 'codex':
        local = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
        official = local / 'Programs/OpenAI/Codex/bin/codex.exe'
        if official.is_file():
            return str(official)
        located = located or shutil.which('codex.cmd')
        if located:
            package = Path(located).parent / 'node_modules/@openai/codex/node_modules/@openai'
            binaries = sorted(package.glob('codex-win32-*/vendor/*-pc-windows-msvc/bin/codex.exe'))
            if len(binaries) == 1:
                return str(binaries[0])
    raise FileNotFoundError('Native codex.exe was not found. Install Codex CLI or pass --codex with the path to codex.exe.')


def profile_home():
    return Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')).resolve()


def profile_catalogue_path(home=None):
    return (Path(home) if home is not None else profile_home()) / 'switch-power/catalogue.json'


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('Refusing symlink state file')
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.switch-power-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Store:
    def __init__(self, root=None):
        profile = hashlib.sha256(os.fsencode(profile_home())).hexdigest()[:20]
        if os.name == 'nt':
            local = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
            default = local / 'Temp' / f'switch-power-{profile}'
        else:
            default = Path('/tmp') / f'switch-power-{os.getuid()}-{profile}'
        self.root = Path(root or os.environ.get('SWITCH_POWER_STATE_DIR', default))

    def ensure_private(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = self.root.lstat()
        if os.name == 'nt':
            private = not (info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        else:
            private = info.st_uid == os.getuid() and not info.st_mode & 0o077
        if not stat.S_ISDIR(info.st_mode) or not private:
            raise ValueError('Switch Power needs a private, user-owned state directory')

    def key(self, session):
        if not isinstance(session, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', session):
            raise ValueError('Valid native session id required (CODEX_THREAD_ID or --session)')
        return hashlib.sha256(session.encode()).hexdigest()

    def session_path(self, session):
        return self.root / (self.key(session) + '.json')

    def catalogue_path(self, session):
        return self.root / (self.key(session) + '.catalogue.json')

    def write_catalogue(self, session, value):
        self.ensure_private()
        atomic_json(self.catalogue_path(session), value)

    def catalogue(self, session):
        self.ensure_private()
        return json.loads(self.catalogue_path(session).read_text(encoding='utf-8'))

    @contextmanager
    def session(self, session):
        with self.locked_state(self.session_path(session)) as state:
            yield state

    def usage(self, session):
        return self.locked_state(self.root / (self.key(session) + '.usage.json'))

    def routing_history(self):
        return self.locked_state(self.root / 'routing-history.json')

    @contextmanager
    def locked_state(self, path):
        self.ensure_private()
        lock = path.with_suffix('.lock')
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'r+b') as stream:
            lock_state(stream.fileno())
            if path.is_symlink():
                raise ValueError('Refusing symlink state')
            state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            if not isinstance(state, dict):
                raise ValueError('Invalid state')
            yield state
            atomic_json(path, state)


def lock_state(fd):
    if os.name != 'nt':
        fcntl.flock(fd, fcntl.LOCK_EX)
        return
    deadline = time.monotonic() + 2
    while True:
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK} or time.monotonic() >= deadline:
                raise
            time.sleep(0.025)


class CodexRPC:
    """Bounded stdio client for the supported native app-server protocol."""
    def __init__(self, codex='codex', env=None, timeout=25):
        self.proc = subprocess.Popen([resolve_codex(codex), 'app-server', '--stdio'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        self.responses = queue.Queue()
        self.reader = threading.Thread(target=self.read_responses, daemon=True)
        self.reader.start()
        self.sequence = 0
        try:
            self.call('initialize', {'clientInfo': {'name': 'switch-power', 'version': '0.1.2'},
                                    'capabilities': {'experimentalApi': True}}, timeout=timeout)
            self.send({'method': 'initialized'})
        except Exception:
            self.close()
            raise

    def read_responses(self):
        try:
            for line in self.proc.stdout:
                self.responses.put(line)
        finally:
            self.responses.put(None)

    def send(self, value):
        self.proc.stdin.write(json.dumps(value).encode() + b'\n')
        self.proc.stdin.flush()

    def call(self, method, params, timeout=25):
        self.sequence += 1
        request_id = self.sequence
        self.send({'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = self.responses.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty:
                break
            if line is None:
                raise RuntimeError('Native Codex app-server exited; inspect codex doctor')
            msg = json.loads(line)
            if msg.get('id') == request_id:
                if 'error' in msg:
                    raise RuntimeError(f'{method}: {msg["error"]}')
                return msg['result']
        raise RuntimeError('Native RPC timeout: ' + method)

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.proc.stdin.close()
        self.reader.join(timeout=0.5)
        self.proc.stdout.close()


def fetch_models(codex='codex', env=None, timeout=25):
    deadline = time.monotonic() + timeout
    rpc = CodexRPC(codex, env=env, timeout=timeout)
    try:
        data, cursor, seen = [], None, set()
        while True:
            page = rpc.call('model/list', {'includeHidden': True, 'limit': 100, 'cursor': cursor},
                            timeout=deadline - time.monotonic())
            data.extend(page['data'])
            cursor = page.get('nextCursor')
            if not cursor:
                return {'data': data, 'fetched_at': time.time()}
            if cursor in seen:
                raise ValueError('Native model/list repeated its pagination cursor')
            seen.add(cursor)
    finally:
        rpc.close()


def cached_profile_catalogue():
    try:
        value = json.loads(profile_catalogue_path().read_text(encoding='utf-8'))
        age = time.time() - value['fetched_at']
        if -60 <= age <= policy.MAX_CATALOGUE_AGE and value['data']:
            return value
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return None


def routing_catalogue(codex):
    value = cached_profile_catalogue()
    if value is not None:
        return value
    try:
        value = fetch_models(codex)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError('No fresh native model catalogue. Switch Power could not refresh it: ' + str(exc)) from exc
    try:
        atomic_json(profile_catalogue_path(), value)
    except (OSError, ValueError):
        # A read-only profile can still use this fresh per-session snapshot.
        pass
    return value


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
    r.add_argument('--track-scope')
    o = subs.add_parser('outcome')
    o.add_argument('--scope', required=True)
    o.add_argument('--verified', choices=['yes', 'no'], required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    store = Store(args.state_dir)
    try:
        store.key(args.session)
        if args.command == 'catalog':
            value = routing_catalogue(args.codex)
            value.update(spawn_models=args.spawn_model, spawn_efforts=args.spawn_effort)
            store.write_catalogue(args.session, value)
            result = value
        elif args.command == 'recommend':
            catalogue = store.catalogue(args.session)
            bucket = policy.routing_bucket(args.kind, args.complexity, args.ambiguity, args.priority)
            samples, coordinator = [], None
            if bucket:
                with store.session(args.session) as state:
                    turn = state.get('turn_id')
                    if args.track_scope and (state.get('needs_resolution') or not turn
                                             or args.track_scope not in state.get('scopes', {})):
                        raise ValueError('Tracking requires a resolved task, captured turn and registered scope')
                    with suppress(OSError, ValueError), store.usage(args.session) as observed:
                        if turn and turn == observed.get('turn'):
                            models = observed.get('coordinators', {})
                            if len(models) == 1:
                                coordinator = next(iter(models))
                        if args.track_scope:
                            usage.track_scope(observed, state['task_id'], args.track_scope, turn, bucket)
                with suppress(OSError, ValueError), store.routing_history() as history:
                    samples = history.get('samples', [])
            result = policy.recommend(catalogue, args.kind, args.complexity,
                                      args.ambiguity, args.priority, samples=samples,
                                      coordinator=coordinator)
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
                        pending = state.get('pending') or {}
                        if (pending.get('model'), pending.get('effort')) == policy.ASTRA_TRIAL:
                            with suppress(OSError, ValueError), store.usage(args.session) as observed:
                                route = observed.get('route')
                                if (route and not route.get('closed') and 'proposal_turn' in route
                                        and route['task_id'] == state['task_id']):
                                    route['continued_turn'] = state.get('turn_id')
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
                    if (args.model, args.effort) == policy.ASTRA_TRIAL:
                        with suppress(OSError, ValueError), store.usage(args.session) as observed:
                            route = observed.get('route')
                            if (route and route['task_id'] == state['task_id']
                                    and route['scope'] == args.scope
                                    and route['first_turn'] == state.get('turn_id')):
                                route['proposal_turn'] = state['turn_id']
                elif args.command == 'outcome':
                    if state.get('needs_resolution') or not state.get('turn_id'):
                        raise ValueError('Resolve the current captured turn before recording an outcome')
                    with store.usage(args.session) as observed:
                        usage.mark_outcome(observed, state['task_id'], args.scope,
                                           state['turn_id'], args.verified == 'yes')
                    result = {'outcome_recorded': True}
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
