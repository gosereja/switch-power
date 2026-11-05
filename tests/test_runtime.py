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

    def test_astra_proposal_records_native_usage_across_consent_and_verification(self):
        c = self.store.catalogue(self.session)
        c['spawn_efforts'].append('ultra')
        astra = next(r for r in c['data'] if r['model'] == 'gpt-6-astra')
        astra['supportedReasoningEfforts'].append({'reasoningEffort': 'ultra'})
        self.store.write_catalogue(self.session, c)
        sol = 'gpt-6.1-sol'
        stop = {'model': sol, 'last_assistant_message': 'Done'}
        self.event('UserPromptSubmit', prompt='Review a distributed protocol')
        self.event('PostModelRequest', model=sol, token_usage={
            'input_tokens': 18, 'cached_input_tokens': 7, 'output_tokens': 3,
            'reasoning_output_tokens': 2, 'total_tokens': 21})
        name = self.ready()
        route = self.cli('recommend', '--kind', 'analysis', '--complexity', '4',
                         '--ambiguity', '2', '--priority', 'quality', '--track-scope', 'review')
        self.assertEqual(route[0]['reasoning_effort'], 'ultra')
        target = ('--model', 'gpt-6-astra', '--effort', 'ultra', '--scope', 'review')
        self.cli('propose', *target, '--reason', 'Check the proof independently')
        launch = dict(tool_name='spawn_agent', tool_input=dict(
            model='gpt-6-astra', reasoning_effort='ultra', task_name=name, fork_turns='none'))
        self.assertEqual(self.event('PreToolUse', **launch)['hookSpecificOutput']
                         ['permissionDecision'], 'deny')
        self.event('Stop', **stop)
        self.event('UserPromptSubmit', turn_id='clarify', prompt='What would the agent verify?')
        self.event('PostModelRequest', turn_id='clarify', model=sol, token_usage={'total_tokens': 4})
        self.cli('task', '--continue')
        self.event('Stop', turn_id='clarify', **stop)

        self.event('UserPromptSubmit', turn_id='t2', prompt='да')
        self.event('PostModelRequest', turn_id='t2', model=sol, token_usage={'total_tokens': 8})
        self.cli('task', '--continue')
        self.cli('grant', *target, '--source', 'live_user', '--turn-id', 't2', '--quote', 'да')
        allowed = self.event('PreToolUse', turn_id='t2', **launch)
        self.assertNotEqual(allowed['hookSpecificOutput'].get('permissionDecision'), 'deny')
        worker = {'agent_id': 'worker', 'turn_id': 'worker-turn', 'model': 'gpt-6-astra'}
        self.event('SubagentStart', **worker)
        self.event('PostModelRequest', token_usage={'total_tokens': 13}, **worker)
        self.event('SubagentStop', **worker)
        self.event('PostModelRequest', turn_id='t2', model=sol, token_usage={'total_tokens': 5})
        self.cli('outcome', '--scope', 'review', '--verified', 'yes')
        self.cli('finish')
        self.event('Stop', turn_id='t2', **stop)
        self.event('Stop', turn_id='t2', **stop)

        with self.store.routing_history() as history:
            sample, = history['samples']
        self.assertEqual(sample['route'], 'astra')
        self.assertEqual(sample['proposal']['total_tokens'], 21)
        self.assertEqual(sample['proposal']['cached_input_tokens'], 7)
        self.assertEqual(sample['clarification']['total_tokens'], 4)
        self.assertEqual(sample['setup']['total_tokens'], 8)
        self.assertEqual(sample['worker']['total_tokens'], 13)
        self.assertEqual(sample['verification']['total_tokens'], 5)
        self.assertEqual(sample['total_tokens'], 51)
        self.assertTrue(sample['verified'])

    def test_routing_history_discards_astra_attempts_missing_proposal_or_verification(self):
        proposal = {'total_tokens': 21}
        route = {'task_id': 'example', 'scope': 'review', 'bucket': 'analysis:4:2',
                 'first_turn': 't2', 'continued_turn': 't2', 'coordinator': 'gpt-6.1-sol',
                 'outcome': {'turn': 't2', 'verified': True}}
        phases = {'setup': {'total_tokens': 8}, 'worker': {'total_tokens': 13}}
        cases = [
            (dict(route, proposal_turn='t1', proposal=proposal), phases),
            (route, dict(phases, verification={'total_tokens': 5})),
        ]
        for trial, counters in cases:
            observed = {'route': trial, 'turn': 't2', 'coordinators': {'gpt-6.1-sol': None},
                        'phases': counters, 'launches': 1, 'workers': {'worker-turn': {}},
                        'measured_launch': 'sp_example__review', 'worker_models': {'gpt-6-astra': None}}
            guard.usage.save_route(observed, self.store, False)
        with self.store.routing_history() as history:
            self.assertEqual(history.get('samples', []), [])

    def test_routing_baseline_requires_complete_sol_usage_and_verified_outcome(self):
        for index, tokens in enumerate([45, None, 12]):
            turn = f'solo-{index}'
            self.event('UserPromptSubmit', turn_id=turn, prompt='Review a protocol')
            self.event('PostModelRequest', turn_id=turn, model='gpt-6.1-sol',
                       token_usage={'total_tokens': tokens})
            self.ready()
            self.cli('recommend', '--kind', 'analysis', '--complexity', '4', '--ambiguity', '2',
                     '--priority', 'quality', '--track-scope', 'review')
            if index != 2:
                self.cli('outcome', '--scope', 'review', '--verified', 'yes')
            self.cli('finish')
            self.event('Stop', turn_id=turn, model='gpt-6.1-sol', last_assistant_message='Done')
        with self.store.routing_history() as history:
            sample, = history['samples']
        self.assertEqual((sample['route'], sample['total_tokens']), ('sol', 45))

    def test_bad_telemetry_does_not_disable_astra_consent(self):
        c = self.store.catalogue(self.session)
        c['spawn_efforts'].append('ultra')
        astra = next(r for r in c['data'] if r['model'] == 'gpt-6-astra')
        astra['supportedReasoningEfforts'].append({'reasoningEffort': 'ultra'})
        self.store.write_catalogue(self.session, c)
        self.event('UserPromptSubmit', prompt='Review a protocol')
        name = self.ready()
        (self.store.root / (self.store.key(self.session) + '.usage.json')).write_text('{broken')
        route = self.cli('recommend', '--kind', 'analysis', '--complexity', '4',
                         '--ambiguity', '2', '--priority', 'quality', '--track-scope', 'review')
        self.assertEqual(route[0]['reasoning_effort'], 'ultra')
        target = ('--model', 'gpt-6-astra', '--effort', 'ultra', '--scope', 'review')
        self.cli('propose', *target, '--reason', 'Independent verification')
        self.event('UserPromptSubmit', turn_id='t2', prompt='да')
        self.cli('task', '--continue')
        self.cli('grant', *target, '--source', 'live_user', '--turn-id', 't2', '--quote', 'да')
        result = self.event('PreToolUse', turn_id='t2', tool_name='spawn_agent', tool_input={
            'model': 'gpt-6-astra', 'reasoning_effort': 'ultra',
            'task_name': name, 'fork_turns': 'none'})
        self.assertNotEqual(result['hookSpecificOutput'].get('permissionDecision'), 'deny')

    def test_native_namespaced_spawn_cannot_bypass_guard(self):
        result = self.event('PreToolUse', tool_name='collaborationspawn_agent', tool_input={})
        self.assertEqual(result['hookSpecificOutput'].get('permissionDecision'), 'deny')

    def test_usage_footer_counts_worker_and_survives_consent_cleanup(self):
        self.event('PostModelRequest', model='gpt-6.1-sol',
                   token_usage={'total_tokens': 21})
        worker = {'agent_id': 'worker', 'turn_id': 'worker-turn', 'model': 'gpt-6-luna'}
        self.event('SubagentStart', **worker)
        self.event('PostModelRequest', token_usage={'total_tokens': 13}, **worker)
        self.event('SubagentStop', **worker)
        self.cli('finish')
        self.assertEqual(self.event('Stop', model='gpt-6.1-sol', last_assistant_message='Done'),
                         {'systemMessage': 'Switch Power · gpt-6.1-sol + gpt-6-luna · 34 tokens'})
        self.assertEqual(self.event('Stop', model='gpt-6.1-sol', last_assistant_message='Done'), {})

    def test_usage_footer_flags_missing_counts_and_excludes_late_workers(self):
        self.event('PostModelRequest', model='gpt-6.1-sol', token_usage={'total_tokens': 21})
        worker = {'agent_id': 'worker', 'turn_id': 'worker-turn', 'model': 'gpt-6-luna'}
        self.event('SubagentStart', **worker)
        self.assertIn('partial', self.event('Stop', model='gpt-6.1-sol',
                                           last_assistant_message='Done')['systemMessage'])
        self.event('PostModelRequest', model='gpt-6.1-sol', turn_id='t2',
                   token_usage={'total_tokens': 10})
        self.event('PostModelRequest', token_usage={'total_tokens': 13}, **worker)
        self.assertEqual(self.event('Stop', turn_id='t2', model='gpt-6.1-sol',
                                    last_assistant_message='Done'),
                         {'systemMessage': 'Switch Power · gpt-6.1-sol · 10 tokens'})

    def test_usage_footer_flags_worker_attempt_without_attribution(self):
        self.event('PostModelRequest', model='gpt-6.1-sol', token_usage={'total_tokens': 21})
        self.event('PostModelRequest', model='gpt-6-luna', agent_id='worker',
                   turn_id='unlinked-worker-turn', token_usage={'total_tokens': 13})
        self.assertEqual(self.event('Stop', model='gpt-6.1-sol', last_assistant_message='Done'),
                         {'systemMessage': 'Switch Power · gpt-6.1-sol · 21 tokens (partial)'})

    def test_usage_footer_reports_missing_data_once(self):
        stop = dict(model='gpt-6.1-sol', last_assistant_message='Done')
        self.assertEqual(self.event('Stop', **stop),
                         {'systemMessage': 'Switch Power · gpt-6.1-sol · token usage unavailable'})
        self.assertEqual(self.event('Stop', **stop), {})

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

    def test_user_prompt_preserves_consent_capture_without_catalogue_discovery(self):
        runtime.profile_catalogue_path().unlink()
        with patch.object(guard, 'fetch_models', side_effect=RuntimeError('Discovery invoked'),
                          create=True) as discovery:
            result = self.event('UserPromptSubmit', prompt='Count the Python files.')
        discovery.assert_not_called()
        self.assertIn('directly', result['hookSpecificOutput']['additionalContext'])
        with self.store.session(self.session) as state:
            self.assertEqual(state['prompt'], 'Count the Python files.')
            self.assertEqual(state['turn_id'], 't1')
            self.assertTrue(state['needs_resolution'])

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

    def test_lazy_catalogue_refresh_is_reused_by_the_next_delegation(self):
        runtime.profile_catalogue_path().unlink()
        fresh = {'fetched_at': time.time(), 'data': [{'id': 'gpt-6-luna'}]}
        with patch.object(runtime, 'fetch_models', return_value=fresh) as fetch:
            self.assertEqual(runtime.routing_catalogue('codex'), fresh)
            self.assertEqual(runtime.routing_catalogue('codex'), fresh)
        fetch.assert_called_once_with('codex')

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
