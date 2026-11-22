"""State-machine regressions: no changes, PR reuse, safe refs and CI dispatch."""
import base64
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs

import yaml
import update_readme_pr as bot

REPO = 'owner/repo'
ORIGINAL = '# Repository\n\n' + bot.START + '\nold\n' + bot.END + '\n\nFooter\n'
COMMITS = [dict(sha='a' * 40, short='aaaaaaa', subject='真实更新 [目录] <tag>')]


class FakeGitHub:
    """Emulate only the GitHub boundary; production rendering/state code is real."""
    def __init__(self):
        self.main = 'base'; self.head = None; self.texts = {'base': ORIGINAL}
        self.prs = []; self.runs = set(); self.calls = []; self.commits = []
        self.files = [{'filename': 'README.md'}]; self.ancestor = 'base'; self.behind = 0
        self.fail_dispatch = None

    def call(self, method, endpoint, payload=None, missing=False):
        self.calls.append((method, endpoint, payload))
        route, _, query = endpoint.partition('?')
        if method == 'GET':
            if route == 'git/ref/heads/main': return {'object': {'sha': self.main}}
            if route == 'git/ref/heads/' + bot.BRANCH: return {'object': {'sha': self.head}} if self.head else None
            if route == 'pulls': return self.prs
            if route.startswith('compare/'):
                return {'files': self.files, 'merge_base_commit': {'sha': self.ancestor}, 'behind_by': self.behind}
            if route == 'contents/README.md':
                sha = parse_qs(query)['ref'][0]
                return {'content': base64.b64encode(self.texts[sha].encode()).decode()}
            if route.startswith('git/commits/'): return {'tree': {'sha': 'main-tree'}}
            if route.endswith('/runs'):
                sha = parse_qs(query)['head_sha'][0]; workflow = route.split('/')[2]
                return {'workflow_runs': [{'head_sha': sha}] if (workflow, sha) in self.runs else []}
        if route == 'git/blobs': self.blob = payload['content']; return {'sha': 'blob'}
        if route == 'git/trees': self.tree = payload; return {'sha': 'tree'}
        if route == 'git/commits':
            self.commits.append(payload); sha = f'commit{len(self.commits)}'
            self.texts[sha] = self.blob; return {'sha': sha}
        if route == 'git/refs' or route == 'git/refs/heads/' + bot.BRANCH:
            if route.endswith(bot.BRANCH): assert payload['force'] is False
            self.head = payload['sha']; self.behind = 0
            for pr in self.prs: pr['head']['sha'] = self.head
            return {}
        if route == 'pulls':
            self.prs = [{'number': 12, 'html_url': 'https://example.com/pr/12',
                         'head': {'ref': bot.BRANCH, 'sha': self.head, 'repo': {'full_name': REPO}}, 'base': {'ref': 'main'}}]
            return self.prs[0]
        if route.endswith('/dispatches'):
            workflow = route.split('/')[2]
            if self.fail_dispatch == workflow: raise RuntimeError('Transient dispatch error')
            assert payload == {'ref': bot.BRANCH}
            self.runs.add((workflow, self.head)); return None
        raise AssertionError((method, endpoint, payload))

    def writes(self):
        return [c for c in self.calls if c[0] != 'GET']


class ReadmeRendering(TestCase):
    def test_absent_markers_and_current_output_are_noop(self):
        api = FakeGitHub()
        self.assertEqual(bot.render('# No marker\n', COMMITS, REPO), '# No marker\n')
        self.assertFalse(bot.update(api, REPO, 'base', ORIGINAL, ORIGINAL)['changed'])
        self.assertEqual(api.calls, [])
        generated = bot.render(ORIGINAL, COMMITS, REPO)
        self.assertEqual(bot.render(generated, COMMITS, REPO), generated)

    def test_apply_without_markers_does_not_require_credentials_or_call_api(self):
        with patch('sys.argv', ['update_readme_pr.py', '--apply']), \
                patch.object(bot, 'git', side_effect=['base\n', '# No recent-commit block\r\n']), \
                patch.object(bot, 'GitHub', side_effect=AssertionError('Unexpected GitHub access')), \
                patch.dict(bot.os.environ, {}, clear=True), redirect_stdout(StringIO()) as output:
            self.assertEqual(bot.main(), 0)
        self.assertIn('no opt-in', output.getvalue())

    def test_malformed_markers_fail_without_writes(self):
        for text in [bot.START, bot.END, bot.END + bot.START, ORIGINAL + bot.START, ORIGINAL + bot.END]:
            with self.subTest(text=text), self.assertRaises(ValueError): bot.render(text, COMMITS, REPO)

    def test_only_block_changes_with_crlf_and_markdown_escaping(self):
        text = ORIGINAL.replace('\n', '\r\n')
        updated = bot.render(text, COMMITS * 7, REPO)
        self.assertEqual(bot.outside_block(text), bot.outside_block(updated))
        self.assertNotIn('\n', updated.replace('\r\n', ''))
        self.assertIn(r'真实更新 \[目录\] &lt;tag&gt;', updated)
        self.assertEqual(updated.count('https://github.com/owner/repo/commit/'), 5)

    def test_real_git_log_excludes_bot_churn_and_preserves_unicode(self):
        with TemporaryDirectory() as folder:
            def git(*args, **kwargs):
                return subprocess.check_output(['git', '-C', folder, *args], **kwargs)
            git('init', '-q'); git('config', 'user.name', 'fixture'); git('config', 'user.email', 'fixture@example.com')
            git('commit', '--allow-empty', '-qm', '真实内容更新 [目录]')
            git('-c', f'user.email={bot.BOT_EMAIL}', 'commit', '--allow-empty', '-qm', bot.MESSAGE)
            git('-c', f'user.email={bot.BOT_EMAIL}', 'commit', '--allow-empty', '-qm', 'Update recent commits in README')
            original_git = bot.git
            with patch.object(bot, 'git', side_effect=lambda *args: git(*args, encoding='utf-8')):
                commits = bot.recent_commits('HEAD')
            self.assertEqual([c['subject'] for c in commits], ['真实内容更新 [目录]'])
            self.assertIs(bot.git, original_git)


class PrLifecycle(TestCase):
    def setUp(self):
        self.api = FakeGitHub(); self.updated = bot.render(ORIGINAL, COMMITS, REPO)

    def run_update(self):
        return bot.update(self.api, REPO, self.api.main, self.api.texts[self.api.main], self.updated)

    def test_create_then_reuse_without_duplicate_commit_pr_or_ci(self):
        first = self.run_update()
        self.assertFalse(first['reused_pr']); self.assertEqual(len(first['dispatched']), 4)
        self.assertEqual(self.api.commits[0]['parents'], ['base'])
        self.assertEqual(self.api.tree['base_tree'], 'main-tree')
        writes = len(self.api.writes()); second = self.run_update()
        self.assertTrue(second['reused_pr']); self.assertEqual(second['pr'], first['pr'])
        self.assertEqual(second['dispatched'], []); self.assertEqual(len(self.api.writes()), writes)
        self.assertEqual(self.api.main, 'base')
        self.assertTrue(all(c[1] != 'git/refs/heads/main' for c in self.api.writes()))

    def test_main_advance_updates_same_pr_preserving_old_head_and_new_main(self):
        first = self.run_update(); old_head = self.api.head
        self.api.main = 'base2'; self.api.texts['base2'] = ORIGINAL.replace('Footer', 'New footer')
        self.api.behind = 1
        self.updated = bot.render(self.api.texts['base2'], COMMITS, REPO)
        second = self.run_update()
        self.assertEqual(first['pr'], second['pr'])
        self.assertEqual(self.api.commits[-1]['parents'], [old_head, 'base2'])
        self.assertIn('New footer', self.api.texts[self.api.head])

    def test_refuses_unrelated_branch_files_or_manual_edits(self):
        self.run_update()
        for files, text in [([{'filename': 'other.txt'}], self.updated),
                            ([{'filename': 'README.md'}], self.updated.replace('Footer', 'Manual change'))]:
            self.api.files = files; self.api.texts[self.api.head] = text
            before = len(self.api.writes())
            with self.assertRaises(ValueError): self.run_update()
            self.assertEqual(len(self.api.writes()), before)

    def test_stale_base_fails_before_any_write(self):
        self.api.main = 'newer'
        with self.assertRaisesRegex(ValueError, 'advanced'):
            bot.update(self.api, REPO, 'base', ORIGINAL, self.updated)
        self.assertEqual(self.api.writes(), [])

    def test_refuses_to_reuse_a_pr_from_another_repository(self):
        self.run_update(); self.api.prs[0]['head']['repo']['full_name'] = 'owner/other-repo'
        before = len(self.api.writes())
        with self.assertRaisesRegex(ValueError, 'does not match'): self.run_update()
        self.assertEqual(len(self.api.writes()), before)

    def test_partial_dispatch_recovers_on_same_pr_and_head(self):
        self.api.fail_dispatch = bot.WORKFLOWS[1]
        with self.assertRaises(RuntimeError): self.run_update()
        head = self.api.head; self.api.fail_dispatch = None
        result = self.run_update()
        self.assertTrue(result['reused_pr']); self.assertEqual(self.api.head, head)
        self.assertEqual(result['dispatched'], list(bot.WORKFLOWS[1:]))
        self.assertEqual(len(self.api.commits), 1)

    def test_api_permission_error_is_not_noop_or_secret_output(self):
        api = bot.GitHub(REPO, 'fixture-secret')
        with patch.object(bot, 'urlopen', side_effect=HTTPError('https://api.github.com', 403, 'Denied', {}, None)):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 403') as error: api.call('POST', 'pulls', {})
            self.assertNotIn('fixture-secret', str(error.exception))


class WorkflowContract(TestCase):
    def test_permissions_concurrency_full_history_and_no_main_push(self):
        root = Path(__file__).resolve().parents[2]
        text = (root / '.github/workflows/update-readme.yml').read_text(encoding='utf-8')
        workflow = yaml.safe_load(text); job = workflow['jobs']['update-readme']
        self.assertEqual(workflow['concurrency'], {'group': 'readme-update-pr', 'cancel-in-progress': False})
        self.assertEqual(job['permissions'], {'contents': 'write', 'pull-requests': 'write', 'actions': 'write'})
        checkout = job['steps'][0]['with']
        self.assertEqual(checkout, {'ref': 'main', 'fetch-depth': 0, 'persist-credentials': False})
        self.assertNotIn('git push', text); self.assertNotIn('||', text)
        for filename in bot.WORKFLOWS:
            data = yaml.safe_load((root / '.github/workflows' / filename).read_text(encoding='utf-8'))
            self.assertIn('workflow_dispatch', data.get('on', data.get(True)))
