import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from test_policy import catalogue
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/switch-power'
sys.path.insert(0, str(PLUGIN / 'hooks'))
try:
    import runtime
    import guard
except ModuleNotFoundError:
    runtime = guard = None


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(runtime, 'Runtime and hook adapters are missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = runtime.Store(Path(self.tmp.name))
        self.session = 'test-session'
        c = catalogue()
        c['fetched_at'] = time.time()
        self.store.write_catalogue(self.session, c)
        profile = patch.dict(os.environ, {'CODEX_HOME': self.tmp.name})
        profile.start()
        self.addCleanup(profile.stop)
        runtime.atomic_json(runtime.profile_catalogue_path(), c)

    def cli(self, *args):
        p = subprocess.run([sys.executable, str(PLUGIN / 'scripts/runtime.py'),
            '--state-dir', self.tmp.name, '--session', self.session, *args],
            capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        return json.loads(p.stdout)

    def ready(self):
        self.cli('task', '--new', '--description', 'Implement and review')
        return self.cli('scope', '--id', 'review', '--description', 'Review only')['task_name']

    def event(self, name, **extra):
        return guard.handle({'hook_event_name': name, 'session_id': self.session,
                             'turn_id': 't1', **extra}, self.store)

    def test_real_cli_and_hook_allow_safe_deny_restricted(self):
        name = self.ready()
        for model, effort, denied in [('gpt-6.1-terra', 'medium', False),
                                      ('gpt-6-astra', 'high', True),
                                      ('gpt-6.1-sol', 'xhigh', True)]:
            result = self.event('PreToolUse', tool_name='collaboration.spawn_agent',
                tool_input={'model': model, 'reasoning_effort': effort,
                            'task_name': name, 'fork_turns': 'none'})
            self.assertEqual(result['hookSpecificOutput'].get('permissionDecision') == 'deny', denied)

    def test_live_prompt_quote_grant_without_second_question(self):
        self.event('UserPromptSubmit', prompt='Используй Astra/xhigh')
        name = self.ready()
        self.cli('grant', '--model', 'gpt-6-astra', '--effort', 'xhigh',
                 '--scope', 'review', '--source', 'live_user', '--turn-id', 't1',
                 '--quote', 'Используй Astra/xhigh')
        r = self.event('PreToolUse', tool_name='spawn_agent', tool_input={
            'model': 'gpt-6-astra', 'reasoning_effort': 'xhigh',
            'task_name': name, 'fork_turns': 'none'})
        self.assertNotEqual(r['hookSpecificOutput'].get('permissionDecision'), 'deny')

    def test_new_task_resets_previous_grant(self):
        self.event('UserPromptSubmit', prompt='Используй Astra/xhigh')
        self.ready()
        self.cli('grant', '--model', 'gpt-6-astra', '--effort', 'xhigh',
                 '--scope', 'review', '--source', 'live_user', '--turn-id', 't1',
                 '--quote', 'Используй Astra/xhigh')
        self.ready()
        self.assertEqual(self.cli('status')['grants'], [])
        self.assertIsNone(self.cli('status')['turn_id'], 'Old user permission must not be replayable into a new task')

    def test_corrupt_state_and_invalid_payload_emit_explicit_deny(self):
        self.ready()
        self.store.session_path(self.session).write_text('{broken')
        result = self.event('PreToolUse', tool_name='spawn_agent', tool_input={})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
        p = subprocess.run([sys.executable, str(PLUGIN / 'hooks/guard.py')],
            input='{broken', text=True, capture_output=True,
            env={**os.environ, 'SWITCH_POWER_STATE_DIR': self.tmp.name})
        self.assertEqual(p.returncode, 0)
        self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_session_ids_cannot_escape_state_directory(self):
        with self.assertRaises(ValueError):
            with self.store.session('../../outside'):
                pass

    def test_rpc_transport_reads_responses_from_child_process_pipe(self):
        worker = '''import json, sys
for line in sys.stdin:
    request = json.loads(line)
    if 'id' in request:
        print(json.dumps({'id': request['id'], 'result': {'method': request['method']}}), flush=True)
'''
        popen = subprocess.Popen
        with patch.object(runtime.subprocess, 'Popen', side_effect=lambda args, **kw:
                popen([sys.executable, '-u', '-c', worker], **kw)):
            rpc = runtime.CodexRPC(sys.executable)
            try:
                self.assertEqual(rpc.call('model/list', {}), {'method': 'model/list'})
            finally:
                rpc.close()

    def test_default_state_is_private_and_shared_across_temp_environments(self):
        with patch.dict(os.environ, {'CODEX_HOME': self.tmp.name, 'TMPDIR': self.tmp.name}):
            os.environ.pop('SWITCH_POWER_STATE_DIR', None)
            first = runtime.Store()
            with patch.dict(os.environ, {'TMPDIR': '/nonexistent'}):
                second = runtime.Store()
            self.assertEqual(first.root, second.root)
            self.assertFalse(first.root.is_relative_to(Path(self.tmp.name)))
            with first.session(self.session) as state:
                state['probe'] = True
            with second.session(self.session) as state:
                self.assertTrue(state['probe'])
            if os.name != 'nt':
                self.assertEqual(first.root.stat().st_mode & 0o777, 0o700)
            self.addCleanup(first.root.rmdir)
            self.addCleanup(first.session_path(self.session).with_suffix('.lock').unlink)
            self.addCleanup(first.session_path(self.session).unlink)

    def test_fresh_profile_catalogue_works_when_native_process_cannot_start(self):
        c = catalogue()
        c['fetched_at'] = time.time()
        with patch.dict(os.environ, {'CODEX_HOME': self.tmp.name}):
            runtime.atomic_json(runtime.profile_catalogue_path(), c)
            self.assertEqual(runtime.routing_catalogue('/missing/codex'), c)
            c['fetched_at'] -= 2 * 86400
            runtime.atomic_json(runtime.profile_catalogue_path(), c)
            with self.assertRaisesRegex(RuntimeError, 'catalogue'):
                runtime.routing_catalogue('/missing/codex')

    def test_incomplete_prompt_cannot_leave_old_consent_active(self):
        name = self.ready()
        self.event('UserPromptSubmit', prompt='Используй Astra/xhigh')
        self.cli('task', '--continue')
        self.cli('grant', '--model', 'gpt-6-astra', '--effort', 'xhigh',
                 '--scope', 'review', '--source', 'live_user', '--turn-id', 't1',
                 '--quote', 'Используй Astra/xhigh')
        guard.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': self.session,
                      'prompt': 'Independent task without native turn metadata'}, self.store)
        with self.store.session(self.session) as state:
            self.assertTrue(state['needs_resolution'])
            self.assertIsNone(state['turn_id'])

    def test_parallel_scope_updates_do_not_lose_work(self):
        from concurrent.futures import ThreadPoolExecutor
        self.ready()
        with ThreadPoolExecutor(max_workers=4) as pool:
            result = list(pool.map(lambda n: self.cli('scope', '--id', 'worker_' + str(n),
                '--description', 'Independent scope ' + str(n)), range(8)))
        self.assertEqual(len(result), 8)
        self.assertEqual(len(self.cli('status')['scopes']), 9)


if __name__ == '__main__':
    unittest.main()
