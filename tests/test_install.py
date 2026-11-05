import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    import install
    import config_edit
    import configure
except ModuleNotFoundError:
    install = config_edit = configure = None


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(install, 'Installation/configuration implementation missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def test_bootstrap_preserves_existing_preferences_and_is_idempotent(self):
        path = self.home / 'AGENTS.md'
        path.write_text('# Personal preferences\nUse Russian.\n')
        install.bootstrap(self.home, True)
        first = path.read_text()
        self.assertIn('Use Russian.', first)
        install.bootstrap(self.home, True)
        self.assertEqual(path.read_text(), first)
        install.bootstrap(self.home, False)
        self.assertEqual(path.read_text(), '# Personal preferences\nUse Russian.\n')

    def test_existing_global_override_receives_bootstrap(self):
        (self.home / 'AGENTS.md').write_text('base\n')
        (self.home / 'AGENTS.override.md').write_text('override\n')
        install.bootstrap(self.home, True)
        self.assertEqual((self.home / 'AGENTS.md').read_text(), 'base\n')
        self.assertIn('Switch Power', (self.home / 'AGENTS.override.md').read_text())
        install.bootstrap(self.home, False)
        self.assertEqual((self.home / 'AGENTS.override.md').read_text(), 'override\n')

    def test_global_hook_fallback_preserves_unrelated_hooks_and_disables_cleanly(self):
        path = self.home / 'hooks.json'
        original = {'description': 'Personal hooks', 'hooks': {
            'Stop': [{'hooks': [{'type': 'command', 'command': 'echo keep'}]}]}}
        path.write_text(json.dumps(original))
        install.global_hooks(self.home, True)
        installed = json.loads(path.read_text())
        self.assertEqual(installed['hooks']['Stop'], original['hooks']['Stop'])
        self.assertIn('PreToolUse', installed['hooks'])
        install.global_hooks(self.home, True)
        self.assertEqual(json.loads(path.read_text()), installed)
        install.global_hooks(self.home, False)
        self.assertEqual(json.loads(path.read_text()), original)

    def test_toml_target_changes_preserve_unrelated_values(self):
        original = '# keep comment\nmodel = "old"\nnotify = ["keep"]\n\n[features]\nfoo = true\n\n[projects."/some/path"]\ntrust_level = "trusted"\n'
        result = config_edit.set_value(original, (), 'model', 'gpt-6.1-sol')
        result = config_edit.set_value(result, (), 'model_reasoning_effort', 'high')
        result = config_edit.set_value(result, ('plugins', 'switch-power@switch-power-personal'), 'enabled', False)
        parsed = tomllib.loads(result)
        self.assertEqual(parsed['model'], 'gpt-6.1-sol')
        self.assertEqual(parsed['model_reasoning_effort'], 'high')
        self.assertEqual(parsed['notify'], ['keep'])
        self.assertEqual(parsed['features'], {'foo': True})
        self.assertEqual(parsed['projects']['/some/path']['trust_level'], 'trusted')
        self.assertFalse(parsed['plugins']['switch-power@switch-power-personal']['enabled'])
        self.assertIn('# keep comment', result)

    def test_multiline_instruction_examples_are_preserved_when_setting_real_model(self):
        text = '''developer_instructions = """
An example, not configuration:
model = "gpt-6-sol"
[features]
example = true
"""
notify = ["keep"]
'''
        before = tomllib.loads(text)
        updated = config_edit.set_value(text, (), 'model', 'gpt-6.1-sol')
        parsed = tomllib.loads(updated)
        self.assertEqual(parsed.get('model'), 'gpt-6.1-sol')
        self.assertEqual(parsed['developer_instructions'], before['developer_instructions'])
        self.assertEqual(parsed['notify'], ['keep'])

    def test_disabling_owns_hooks_independently_of_python_interpreter(self):
        install.global_hooks(self.home, True)
        path = self.home / 'hooks.json'
        value = json.loads(path.read_text())
        import shlex
        for groups in value['hooks'].values():
            for group in groups:
                for handler in group['hooks']:
                    tokens = shlex.split(handler['command'])
                    handler['command'] = '/previous/python ' + shlex.quote(tokens[-1])
        path.write_text(json.dumps(value))
        install.global_hooks(self.home, False)
        self.assertFalse(path.exists(), 'No Switch Power hooks should survive interpreter replacement')

    def test_configure_restore_does_not_overwrite_later_user_edit(self):
        p = self.home / 'config.toml'
        p.write_text('model = "gpt-6-sol"\nmodel_reasoning_effort = "medium"\nnotify = ["keep"]\n')
        configure.apply(self.home, 'gpt-6.1-sol', 'high')
        self.assertEqual(tomllib.loads(p.read_text())['model_reasoning_effort'], 'high')
        configure.restore(self.home)
        self.assertEqual(tomllib.loads(p.read_text())['model'], 'gpt-6-sol')
        self.assertEqual(tomllib.loads(p.read_text())['notify'], ['keep'])
        configure.apply(self.home, 'gpt-6.1-sol', 'high')
        p.write_text(config_edit.set_value(p.read_text(), (), 'model', 'user-changed'))
        with self.assertRaises(ValueError):
            configure.restore(self.home)
        self.assertEqual(tomllib.loads(p.read_text())['model'], 'user-changed')


if __name__ == '__main__':
    unittest.main()
