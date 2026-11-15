"""Update the opt-in recent-commits block through a reusable PR, never main."""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

START = '<!-- COMMIT-START -->'
END = '<!-- COMMIT-END -->'
BRANCH = 'codex/auto-readme-updates'
MESSAGE = 'docs: update README recent commits'
BOT_EMAIL = '41898282+github-actions[bot]@users.noreply.github.com'
WORKFLOWS = ('check-links.yml', 'format-check.yml', 'generate-index.yml', 'browser-regression.yml')


def bounds(text: str) -> tuple[int, int] | None:
    if START not in text and END not in text:
        return None
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('Recent-commit markers must occur exactly once as a pair')
    left, right = text.index(START) + len(START), text.index(END)
    if left > right:
        raise ValueError('Recent-commit markers are reversed')
    return left, right


def outside_block(text: str) -> str:
    span = bounds(text)
    if span is None:
        raise ValueError('Managed branch has no recent-commit markers')
    return text[:span[0]] + text[span[1]:]


def render(text: str, commits: list[dict], repository: str) -> str:
    span = bounds(text)
    if span is None:
        return text
    nl = '\r\n' if '\r\n' in text else '\n'
    lines = ['## 最近提交', '']
    for commit in commits[:5]:
        subject = html.escape(commit['subject'], quote=False)
        subject = re.sub(r'([\\`*_\[\]()|])', r'\\\1', subject)
        lines.append(f"- {subject} ([{commit['short']}](https://github.com/{repository}/commit/{commit['sha']}))")
    return text[:span[0]] + nl * 2 + nl.join(lines) + nl * 2 + text[span[1]:]


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args]).decode('utf-8')


def recent_commits(ref: str) -> list[dict]:
    # Ignore merge commits and our own updates, so merging the bot PR cannot
    # generate another README update forever. -z keeps Unicode subjects intact.
    fields = git('log', ref, '--no-merges', '-z', '--format=%H%x00%h%x00%s%x00%ae').rstrip('\0').split('\0')
    commits = []
    for i in range(0, len(fields), 4):
        sha, short, subject, email = fields[i:i + 4]
        if email == BOT_EMAIL and subject in {MESSAGE, 'Update recent commits in README'}:
            continue
        commits.append(dict(sha=sha, short=short, subject=subject))
        if len(commits) == 5:
            break
    return commits


class GitHub:
    def __init__(self, repository: str, token: str):
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', repository):
            raise ValueError('Expected repository owner/name')
        if not token:
            raise ValueError('GH_TOKEN is required for --apply when content changes')
        self.root = f'https://api.github.com/repos/{repository}/'
        self.token = token

    def call(self, method: str, endpoint: str, payload=None, missing=False):
        request = Request(self.root + endpoint, method=method,
                          data=None if payload is None else json.dumps(payload).encode(),
                          headers={'Authorization': f'Bearer {self.token}',
                                   'Accept': 'application/vnd.github+json',
                                   'X-GitHub-Api-Version': '2022-11-28',
                                   'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=60) as response:
                data = response.read()
                return json.loads(data) if data else None
        except HTTPError as error:
            if error.code == 404 and missing:
                return None
            # Do not print headers/tokens or treat authorization failures as no-op.
            raise RuntimeError(f'GitHub {method} {endpoint.split("?")[0]} failed: HTTP {error.code}') from None


def readme_at(api, sha: str) -> str:
    data = api.call('GET', 'contents/README.md?' + urlencode({'ref': sha}))
    return base64.b64decode(data['content']).decode('utf-8')


def ensure_ci(api, head: str) -> list[str]:
    dispatched = []
    for workflow in WORKFLOWS:
        endpoint = f'actions/workflows/{workflow}/runs'
        runs = api.call('GET', endpoint + '?' + urlencode({'head_sha': head, 'event': 'workflow_dispatch', 'per_page': 100}))
        # Dispatches are idempotent per head/workflow. A partial API failure can
        # be repaired next run without a second PR/commit or repeated CI runs.
        if any(r['head_sha'] == head for r in runs['workflow_runs']):
            continue
        api.call('POST', f'actions/workflows/{workflow}/dispatches', {'ref': BRANCH})
        dispatched.append(workflow)
    return dispatched


def update(api, repository: str, base: str, original: str, updated: str) -> dict:
    if original == updated:
        return {'changed': False, 'reason': 'no content changes'}
    current = api.call('GET', 'git/ref/heads/main')['object']['sha']
    if current != base:
        raise ValueError('main advanced after checkout; retry from latest main')
    pulls = api.call('GET', 'pulls?' + urlencode({'state': 'open', 'base': 'main', 'head': repository.split('/')[0] + ':' + BRANCH, 'per_page': 100}))
    if len(pulls) > 1:
        raise ValueError('Multiple open update PRs; refusing an ambiguous update')
    ref = api.call('GET', 'git/ref/heads/' + BRANCH, missing=True)
    previous = ref['object']['sha'] if ref else None
    if pulls and (not previous or pulls[0]['head']['ref'] != BRANCH or pulls[0]['base']['ref'] != 'main'
                  or pulls[0]['head']['sha'] != previous or pulls[0]['head']['repo']['full_name'] != repository):
        raise ValueError('Existing update PR/ref does not match the managed branch')
    existing_text, behind = None, 0
    if previous:
        comparison = api.call('GET', f'compare/{base}...{previous}')
        if any(f['filename'] != 'README.md' for f in comparison['files']):
            raise ValueError('Managed branch contains unrelated files; refusing to replace them')
        existing_text = readme_at(api, previous)
        ancestor_text = readme_at(api, comparison['merge_base_commit']['sha'])
        if outside_block(existing_text) != outside_block(ancestor_text):
            raise ValueError('Managed branch has manual README edits outside the generated block')
        behind = comparison['behind_by']
    head = previous
    if existing_text != updated or behind:
        base_commit = api.call('GET', 'git/commits/' + base)
        blob = api.call('POST', 'git/blobs', {'content': updated, 'encoding': 'utf-8'})
        tree = api.call('POST', 'git/trees', {'base_tree': base_commit['tree']['sha'],
                        'tree': [{'path': 'README.md', 'mode': '100644', 'type': 'blob', 'sha': blob['sha']}]})
        parents = list(dict.fromkeys([previous, base] if previous else [base]))
        commit = api.call('POST', 'git/commits', {'message': MESSAGE, 'tree': tree['sha'], 'parents': parents,
                          'author': {'name': 'github-actions[bot]', 'email': BOT_EMAIL}})
        if api.call('GET', 'git/ref/heads/main')['object']['sha'] != base:
            raise ValueError('main advanced while preparing update; no branch written')
        head = commit['sha']
        if previous:
            # Both old head and latest main are parents: fast-forward only,
            # retain history and satisfy strict up-to-date protection. No force push.
            api.call('PATCH', 'git/refs/heads/' + BRANCH, {'sha': head, 'force': False})
        else:
            api.call('POST', 'git/refs', {'ref': 'refs/heads/' + BRANCH, 'sha': head})
    if pulls:
        pr = pulls[0]
    else:
        pr = api.call('POST', 'pulls', {'base': 'main', 'head': BRANCH, 'draft': False,
                      'title': 'docs: 更新 README 最近提交',
                      'body': '自动更新 COMMIT-START / COMMIT-END 之间的最近提交区块。\n\n'
                              '复用固定更新分支；仅更新生成区块。需等待全部必需 CI，通过普通 PR 流程合并，不自动审批或绕过保护。'})
    workflows = ensure_ci(api, head)
    return {'changed': True, 'head': head, 'pr': pr['number'], 'url': pr['html_url'],
            'reused_pr': bool(pulls), 'dispatched': workflows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=os.getenv('GITHUB_REPOSITORY', 'gonglei007/GameDevMind'))
    parser.add_argument('--apply', action='store_true', help='Write automation branch/PR; default is a local dry-run')
    args = parser.parse_args()
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', args.repository):
        raise ValueError('Expected repository owner/name')
    base = git('rev-parse', 'origin/main').strip()
    original = git('show', f'{base}:README.md')
    if bounds(original) is None:
        result = {'changed': False, 'reason': 'README has no opt-in recent-commit markers'}
    else:
        updated = render(original, recent_commits(base), args.repository)
        if updated == original:
            result = {'changed': False, 'reason': 'no content changes'}
        elif not args.apply:
            result = {'changed': True, 'dry_run': True, 'base': base, 'branch': BRANCH}
        else:
            api = GitHub(args.repository, os.getenv('GH_TOKEN', ''))
            result = update(api, args.repository, base, original, updated)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a', encoding='utf-8') as summary:
            summary.write('## README update PR\n\n```json\n' + output + '\n```\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
