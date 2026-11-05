import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/switch-power/scripts'))
try:
    import policy
except ModuleNotFoundError:
    policy = None


def catalogue():
    # Fixture values are hand checked against this session's tool schema.
    rows = []
    for model, desc in [
        ('gpt-6.1-sol', 'Complex coding and analysis'),
        ('gpt-6.1-terra', 'Visual reasoning and computer use'),
        ('gpt-6-luna', 'Focused high-volume tasks'),
        ('gpt-6-sol', 'Previous workhorse'),
        ('gpt-6-astra', 'Most demanding reasoning'),
        ('gpt-reserve', 'Reserve'),
    ]:
        rows.append({'model': model, 'description': desc,
                     'supportedReasoningEfforts': [
                         {'reasoningEffort': e} for e in ['low', 'medium', 'high', 'xhigh']],
                     'upgrade': None, 'upgradeInfo': None})
    return {'fetched_at': 1000, 'data': rows,
            'spawn_models': [m['model'] for m in rows[:-1]],
            'spawn_efforts': ['low', 'medium', 'high', 'xhigh']}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(policy, 'Policy implementation is missing')
        self.c = catalogue()
        self.s = policy.new_task('Implement feature')
        policy.add_scope(self.s, 'review', 'Review implementation only')

    def check(self, model, effort, scope='review', state=None):
        s = state or self.s
        return policy.check(self.c, s, model, effort,
                            f"sp_{s['task_id']}__{scope}", 'none', now=1001)

    def consent(self, model, effort, scope='review', text='Используй Astra/xhigh'):
        policy.capture_prompt(self.s, 'turn-1', text)
        policy.continue_task(self.s)
        policy.grant(self.s, model, effort, scope, 'live_user', 'turn-1', text)

    def test_automatic_families_and_efforts(self):
        for m in ['gpt-6.1-sol', 'gpt-6-sol', 'gpt-6.1-terra', 'gpt-6-luna']:
            for e in ['low', 'medium', 'high']:
                with self.subTest(m=m, e=e):
                    self.assertTrue(self.check(m, e)['allowed'])

    def test_astra_and_above_high_are_denied_without_consent(self):
        for m, e in [('gpt-6-astra', 'low'), ('gpt-6-astra', 'high'),
                     ('gpt-6.1-sol', 'xhigh')]:
            self.assertFalse(self.check(m, e)['allowed'])

    def test_direct_permission_needs_no_second_question(self):
        self.consent('gpt-6-astra', 'xhigh')
        self.assertTrue(self.check('gpt-6-astra', 'xhigh')['allowed'])
        self.assertTrue(self.check('gpt-6-astra', 'xhigh')['allowed'])
        self.assertFalse(self.check('gpt-6-astra', 'high')['allowed'])

    def test_grant_does_not_escape_scope_or_next_task(self):
        self.consent('gpt-6-astra', 'xhigh')
        policy.add_scope(self.s, 'write', 'Write implementation')
        self.assertFalse(self.check('gpt-6-astra', 'xhigh', 'write')['allowed'])
        other = policy.new_task('Independent second task')
        policy.add_scope(other, 'review', 'Review second task')
        self.assertFalse(self.check('gpt-6-astra', 'xhigh', state=other)['allowed'])

    def test_documents_silence_agents_and_stale_turn_are_not_consent(self):
        policy.capture_prompt(self.s, 'turn-1', 'Используй Astra/xhigh')
        policy.continue_task(self.s)
        for src, turn, quote in [('document', 'turn-1', 'Используй Astra/xhigh'),
                                 ('assistant', 'turn-1', 'Используй Astra/xhigh'),
                                 ('live_user', 'turn-1', ''),
                                 ('live_user', 'old-turn', 'Используй Astra/xhigh'),
                                 ('live_user', 'turn-1', 'несуществующая цитата')]:
            with self.subTest(src=src, turn=turn, quote=quote):
                with self.assertRaises(ValueError):
                    policy.grant(self.s, 'gpt-6-astra', 'xhigh', 'review', src, turn, quote)
        self.assertFalse(self.check('gpt-6-astra', 'xhigh')['allowed'])

    def test_followup_preserves_task_grant_after_explicit_boundary_resolution(self):
        self.consent('gpt-6-astra', 'xhigh')
        policy.capture_prompt(self.s, 'turn-2', 'Продолжай эту же проверку')
        self.assertFalse(self.check('gpt-6-astra', 'xhigh')['allowed'])
        policy.continue_task(self.s)
        self.assertTrue(self.check('gpt-6-astra', 'xhigh')['allowed'])

    def test_short_yes_requires_prior_exact_proposal(self):
        policy.capture_prompt(self.s, 'first', 'Проверь код')
        policy.continue_task(self.s)
        policy.propose(self.s, 'gpt-6-astra', 'high', 'review', 'Deep independent review')
        policy.capture_prompt(self.s, 'second', 'да')
        policy.continue_task(self.s)
        policy.grant(self.s, 'gpt-6-astra', 'high', 'review', 'live_user', 'second', 'да')
        self.assertTrue(self.check('gpt-6-astra', 'high')['allowed'])
        with self.assertRaises(ValueError):
            policy.grant(self.s, 'gpt-6-astra', 'xhigh', 'review', 'live_user', 'second', 'да')

    def test_full_proposal_approval_needs_exact_tuple_and_later_turn(self):
        text = 'Согласен на этот вариант'
        policy.capture_prompt(self.s, 'first', text)
        policy.continue_task(self.s)
        policy.propose(self.s, 'gpt-6-astra', 'high', 'review', 'Deep independent review')
        with self.assertRaises(ValueError):
            policy.grant(self.s, 'gpt-6-astra', 'high', 'review', 'live_user', 'first', text)
        policy.capture_prompt(self.s, 'second', text)
        policy.continue_task(self.s)
        with self.assertRaises(ValueError):
            policy.grant(self.s, 'gpt-6-astra', 'xhigh', 'review', 'live_user', 'second', text)
        policy.grant(self.s, 'gpt-6-astra', 'high', 'review', 'live_user', 'second', text)
        self.assertTrue(self.check('gpt-6-astra', 'high')['allowed'])

    def test_unavailable_model_effort_stale_catalogue_and_inheritance(self):
        for m, e in [('imagined-model', 'high'), ('gpt-reserve', 'high'),
                     ('gpt-6.1-sol', 'ultra')]:
            self.assertFalse(self.check(m, e)['allowed'])
        self.assertFalse(policy.check(self.c, self.s, 'gpt-6.1-sol', 'high',
            f"sp_{self.s['task_id']}__review", 'all', now=1001)['allowed'])
        self.assertFalse(policy.check(self.c, self.s, 'gpt-6.1-sol', 'high',
            f"sp_{self.s['task_id']}__review", 'none', now=100000)['allowed'])

    def test_child_cannot_use_another_task_scope(self):
        self.assertFalse(policy.check(self.c, self.s, 'gpt-6.1-sol', 'high',
            'sp_foreign__review', 'none', now=1001)['allowed'])

    def test_failed_tuple_is_not_retried_without_bound(self):
        policy.mark_failed(self.s, 'gpt-6.1-sol', 'high', 'review', 'model unavailable')
        self.assertFalse(self.check('gpt-6.1-sol', 'high')['allowed'])
        self.assertTrue(self.check('gpt-6.1-terra', 'medium')['allowed'])

    def test_upgrade_uses_vendor_metadata_and_requires_available_sol_high(self):
        self.assertIsNone(policy.upgrade(self.c, 'gpt-6-sol'))
        self.c['data'][3]['upgradeInfo'] = {'model': 'gpt-6.1-sol'}
        self.assertEqual(policy.upgrade(self.c, 'gpt-6-sol'), 'gpt-6.1-sol')
        self.c['data'][3]['upgradeInfo'] = {'model': 'gpt-6-astra'}
        with self.assertRaises(ValueError):
            policy.upgrade(self.c, 'gpt-6-sol')
        self.c['data'][3]['upgradeInfo'] = {'model': 'made-up-sol'}
        with self.assertRaises(ValueError):
            policy.upgrade(self.c, 'gpt-6-sol')

    def test_demanding_quality_work_proposes_supported_astra_ultra_early(self):
        self.c['spawn_efforts'].append('ultra')
        astra = next(r for r in self.c['data'] if r['model'] == 'gpt-6-astra')
        astra['supportedReasoningEfforts'].append({'reasoningEffort': 'ultra'})
        route = policy.recommend(self.c, 'analysis', 4, 2, 'quality', now=1001)
        self.assertEqual((route[0]['model'], route[0]['reasoning_effort']),
                         ('gpt-6-astra', 'ultra'))
        self.assertTrue(route[0]['requires_consent'])
        self.assertEqual(route[0]['evidence']['decision'], 'trial')
        for complexity, priority in [(3, 'quality'), (4, 'balanced')]:
            route = policy.recommend(self.c, 'analysis', complexity, 2, priority, now=1001)
            self.assertFalse(any(row['reasoning_effort'] == 'ultra' for row in route))
        self.c['spawn_efforts'].remove('ultra')
        route = policy.recommend(self.c, 'analysis', 4, 2, 'quality', now=1001)
        self.assertFalse(any(row['reasoning_effort'] == 'ultra' for row in route))

    def test_observed_usage_drives_comparison_and_sol_calibration(self):
        self.c['spawn_efforts'].append('ultra')
        astra = next(r for r in self.c['data'] if r['model'] == 'gpt-6-astra')
        astra['supportedReasoningEfforts'].append({'reasoningEffort': 'ultra'})
        coordinator = 'gpt-6.1-sol'
        sample = dict(bucket='analysis:4:2', coordinator=coordinator, recorded_at=1000,
                      route='astra', total_tokens=150, verified=True)
        baseline = dict(sample, route='sol', total_tokens=100)
        irrelevant = [dict(baseline, bucket='code:4:2'), dict(baseline, coordinator='gpt-6-sol'),
                      dict(baseline, recorded_at=-30 * 86400)]

        def rank(samples):
            return policy.recommend(self.c, 'analysis', 4, 2, 'quality', now=1001,
                                    coordinator=coordinator, samples=samples)

        ranked = rank([sample] * 3 + irrelevant)
        self.assertEqual(ranked[0]['model'], coordinator)
        self.assertEqual(ranked[-1]['evidence']['decision'], 'measure_sol')
        ranked = rank([sample] * 3 + [baseline] * 2 + [dict(baseline, verified=False)])
        self.assertEqual(ranked[-1]['evidence']['decision'], 'measure_sol')
        ranked = rank([dict(sample, verified=False)] * 3)
        self.assertEqual(ranked[-1]['evidence']['decision'], 'measure_sol')
        ranked = rank([dict(sample, verified=False)] * 3 + [baseline] * 3)
        self.assertEqual(ranked[-1]['evidence']['decision'], 'prefer_sol')
        ranked = rank([sample] * 3 + [baseline] * 3)
        self.assertEqual(ranked[0]['model'], coordinator)
        self.assertEqual(ranked[-1]['evidence']['decision'], 'prefer_sol')
        self.assertEqual(ranked[-1]['evidence']['astra']['median_total_tokens'], 150)
        ranked = rank([dict(sample, total_tokens=120)] * 3 + [baseline] * 3)
        self.assertEqual(ranked[0]['evidence']['decision'], 'propose')
        ranked = rank([sample] * 3 + [baseline] * 3 + [dict(baseline, verified=False)])
        self.assertEqual(ranked[0]['evidence']['decision'], 'propose')

    def test_recommendation_uses_catalogue_and_launch_intersection(self):
        result = policy.recommend(self.c, 'visual', 1, 1, 'balanced', now=1001)
        self.assertEqual(result[0]['model'], 'gpt-6.1-terra')
        self.c['spawn_models'].remove('gpt-6.1-terra')
        result = policy.recommend(self.c, 'visual', 1, 1, 'balanced', now=1001)
        self.assertNotIn('gpt-6.1-terra', [m['model'] for m in result])
        self.assertTrue(any(m['requires_consent'] for m in result if m['model'] == 'gpt-6-astra'))


if __name__ == '__main__':
    unittest.main()
